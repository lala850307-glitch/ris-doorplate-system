"""
試題 2 - 資料庫操作層（PostgreSQL + 連線池）

對外提供三個函式：
    init_pool()                     → 啟動時建立連線池
    check_connection()              → 確認 DB 連線是否正常（健康檢查用）
    query_records(city, township,   → 依縣市 + 鄉鎮市區查詢門牌資料（含分頁）
                  limit, offset)
"""
from __future__ import annotations

import logging

import psycopg2
import psycopg2.extras
import psycopg2.pool

from config import DB_CONFIG

logger = logging.getLogger("api")

# ── 連線池（應用程式生命週期內共用）─────────────────────────
_pool: psycopg2.pool.SimpleConnectionPool | None = None


def init_pool() -> None:
    """
    建立 PostgreSQL 連線池。
    FastAPI startup 事件呼叫，確保 API 啟動時 DB 連線就緒。
    minconn=1：至少維持 1 條連線
    maxconn=10：最多允許 10 條並發連線
    """
    global _pool
    _pool = psycopg2.pool.SimpleConnectionPool(
        minconn=1,
        maxconn=10,
        **DB_CONFIG,
    )
    logger.info("資料庫連線池已建立（min=1, max=10）")


def _get_conn():
    """從連線池取得一條連線。"""
    if _pool is None:
        raise RuntimeError("連線池尚未初始化，請先呼叫 init_pool()")
    return _pool.getconn()


def _put_conn(conn) -> None:
    """將連線歸還連線池。"""
    if _pool:
        _pool.putconn(conn)


# ── Public API ────────────────────────────────────────────────
def check_connection() -> str:
    """
    嘗試從連線池取得連線並測試，回傳狀態字串。
    - 成功 → "connected"
    - 失敗 → "error: <訊息>"
    """
    try:
        conn = _get_conn()
        _put_conn(conn)
        return "connected"
    except Exception as e:
        logger.error(f"健康檢查：資料庫連線失敗 → {e}")
        return f"error: {e}"


def query_records(
    city: str,
    township: str,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """
    依縣市 + 鄉鎮市區查詢門牌初編資料（含分頁）。

    Args:
        city:     縣市名稱（例：「台北市」）
        township: 鄉鎮市區名稱（例：「大安區」）
        limit:    每頁筆數（預設 100，最大 1000）
        offset:   跳過筆數（預設 0）

    Returns:
        (records, total)
        - records: 當頁資料列表
        - total:   符合條件的總筆數

    Raises:
        Exception: 資料庫連線或查詢失敗時向上拋出
    """
    conn = _get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # 查總筆數
        cur.execute(
            "SELECT COUNT(*) FROM door_plate_data "
            "WHERE city = %s AND township = %s",
            (city, township),
        )
        total = cur.fetchone()["count"]

        # 查當頁資料
        cur.execute(
            """
            SELECT city, township, village,
                   address, registration_date, registration_type
            FROM door_plate_data
            WHERE city     = %s
              AND township = %s
            ORDER BY id
            LIMIT %s OFFSET %s
            """,
            (city, township, limit, offset),
        )
        rows = [dict(row) for row in cur.fetchall()]
        return rows, total
    finally:
        _put_conn(conn)
