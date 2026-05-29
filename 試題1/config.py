"""
試題 1 - 爬蟲設定檔
集中管理 URL、查詢條件、資料庫設定、輸出路徑等所有常數。
"""
import os
from pathlib import Path

# ── 路徑 ──────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent
OUTPUT_DIR  = ROOT / "output"
LOG_DIR     = ROOT / "logs"
CAPTCHA_DIR = ROOT / "output" / "captcha"

# ── 目標網站 URL（分析自 Chrome DevTools Network XHR 請求）──
BASE_URL    = "https://www.ris.gov.tw"
PORTAL_URL  = f"{BASE_URL}/app/portal/3053"
MAIN_URL    = f"{BASE_URL}/info-doorplate/app/doorplate/main"
MAP_URL     = f"{BASE_URL}/info-doorplate/app/doorplate/map"
QUERY_URL   = f"{BASE_URL}/info-doorplate/app/doorplate/query"
INQUIRY_URL = f"{BASE_URL}/info-doorplate/app/doorplate/inquiry/date"
CAPTCHA_URL = f"{BASE_URL}/info-doorplate/captcha/image"

# ── 查詢條件 ──────────────────────────────────────────────────
CITY_CODE     = "63000000"   # 台北市代碼
TARGET_CITY   = "台北市"
START_DATE    = "1140901"    # 民國 7 碼（API 格式，無分隔符）
END_DATE      = "1141130"
CATEGORY      = "門牌初編"
REGISTER_KIND = "1"          # 門牌初編 = option value "1"

TAIPEI_DISTRICTS = {
    "松山區": "63000010",
    "信義區": "63000020",
    "大安區": "63000030",
    "中山區": "63000040",
    "中正區": "63000050",
    "大同區": "63000060",
    "萬華區": "63000070",
    "文山區": "63000080",
    "南港區": "63000090",
    "內湖區": "63000100",
    "士林區": "63000110",
    "北投區": "63000120",
}

# ── HTTP 設定 ─────────────────────────────────────────────────
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
REQUEST_TIMEOUT   = 30    # 單次 HTTP 請求逾時（秒）
MAX_RETRY         = 3     # HTTP 失敗重試次數
MAX_CAPTCHA_RETRY = 10    # 驗證碼最多嘗試次數（前 8 次 OCR，最後 2 次人工）

# ── 資料庫設定（PostgreSQL，從環境變數讀取）──────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME",     "crawldb"),
    "user":     os.getenv("DB_USER",     "admin"),
    "password": os.getenv("DB_PASSWORD", "admin123"),
    "sslmode":  os.getenv("DB_SSLMODE",  "disable"),  # 地端=disable，雲地=require
}

# ── CSV 欄位定義 ──────────────────────────────────────────────
CSV_HEADERS    = ["city", "township", "village", "address", "registration_date", "registration_type"]
CSV_HEADERS_ZH = ["縣市", "鄉鎮市區", "村里", "門牌地址", "編訂日期", "編訂類別"]
