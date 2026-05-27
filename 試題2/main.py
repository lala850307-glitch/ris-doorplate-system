"""
試題 2 - FastAPI 查詢 API

端點：
  GET  /health  健康檢查（確認 API 與 DB 狀態）
  POST /query   依縣市 + 鄉鎮市區查詢門牌初編資料

執行方式：
  uvicorn main:app --host 0.0.0.0 --port 8000 --reload

Swagger UI（互動式文件）：
  http://localhost:8000/docs
"""
import logging
import sys
import time
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

load_dotenv()

from config import API_DESCRIPTION, API_TITLE, API_VERSION
from db import check_connection, init_pool, query_records
from models import DoorPlateRecord, HealthResponse, QueryRequest, QueryResponse
from notify import send_notify



# ─────────────────────────────────────────────────────────────
# Logger 設定
# ─────────────────────────────────────────────────────────────
def setup_logger() -> logging.Logger:
    """
    建立 API logger，輸出到 stdout。
    Promtail 從 Docker stdout 收集，格式與試題1 crawler 一致。
    """
    logger = logging.getLogger("api")
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    logger.addHandler(ch)
    return logger


logger = setup_logger()


# ─────────────────────────────────────────────────────────────
# FastAPI 應用程式
# ─────────────────────────────────────────────────────────────
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
)

# 掛載靜態檔案目錄（index.html 查詢介面）
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    """根路徑 → 導向查詢介面"""
    return RedirectResponse(url="/static/index.html")


# ─────────────────────────────────────────────────────────────
# 生命週期事件
# ─────────────────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    """
    FastAPI 啟動時自動建立 DB 連線池。
    確保第一個請求進來時連線池已就緒，不需每次請求重新建立連線。
    """
    init_pool()
    logger.info("FastAPI 啟動完成，DB 連線池已就緒")

# 允許所有來源的 CORS（開發 / 測試環境用）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────
# Middleware：自動記錄每個 Request
# ─────────────────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    全域 Request log：記錄 method、path、status code、耗時。
    Promtail 收集後可在 Grafana 查詢 API 歷史紀錄。
    """
    start   = time.time()
    response = await call_next(request)
    elapsed = round((time.time() - start) * 1000, 2)
    logger.info(
        f"method={request.method} "
        f"path={request.url.path} "
        f"status={response.status_code} "
        f"duration={elapsed}ms"
    )
    return response


# ─────────────────────────────────────────────────────────────
# 端點
# ─────────────────────────────────────────────────────────────
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="健康檢查",
    tags=["系統"],
)
def health_check():
    """
    確認 API 服務與 PostgreSQL 資料庫是否正常。

    - **status**：固定回傳 `"ok"`
    - **db**：`"connected"` 代表 DB 正常；否則顯示錯誤訊息
    - **timestamp**：目前 UTC 時間
    """
    return HealthResponse(
        status="ok",
        db=check_connection(),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.post(
    "/query",
    response_model=QueryResponse,
    summary="查詢門牌資料",
    tags=["查詢"],
)
def query_door_plate(
    req: QueryRequest,
    limit:  int = Query(default=100, ge=1, le=1000, description="每頁筆數（1–1000，預設 100）"),
    offset: int = Query(default=0,   ge=0,           description="跳過筆數（預設 0）"),
):
    """
    依縣市 + 鄉鎮市區查詢門牌初編資料（支援分頁）。

    **Request Body：**
    ```json
    { "city": "台北市", "township": "大安區" }
    ```

    **Query Params（可選）：**
    - `limit`：每頁筆數，預設 100，最大 1000
    - `offset`：跳過筆數，預設 0

    **Response：**
    ```json
    {
      "city": "台北市", "township": "大安區",
      "total": 256, "count": 100,
      "limit": 100, "offset": 0,
      "data": [...]
    }
    ```

    **異常行為：**
    - 查詢結果為空（total=0）→ WARNING log + Email 通報
    - 資料庫錯誤 → HTTP 500
    """
    start = time.time()
    logger.info(
        f"查詢請求 | city={req.city} township={req.township} "
        f"limit={limit} offset={offset}"
    )

    # 查詢資料庫
    try:
        rows, total = query_records(req.city, req.township, limit=limit, offset=offset)
    except Exception as e:
        logger.error(
            f"資料庫查詢失敗 | city={req.city} township={req.township} | error={e}"
        )
        raise HTTPException(status_code=500, detail=f"資料庫查詢失敗：{e}")

    count   = len(rows)
    elapsed = round((time.time() - start) * 1000, 2)
    logger.info(
        f"查詢完成 | city={req.city} township={req.township} "
        f"| total={total} count={count} | duration={elapsed}ms"
    )

    # 查詢結果為空（total=0 代表 DB 完全沒有這個區域的資料）
    if total == 0:
        msg = (
            f"[⚠️ 查詢異常] {req.city}{req.township} 查無資料，"
            f"請確認爬蟲是否已執行"
        )
        logger.warning(msg)
        send_notify(msg)

    return QueryResponse(
        city=req.city,
        township=req.township,
        total=total,
        count=count,
        limit=limit,
        offset=offset,
        data=rows,
    )
