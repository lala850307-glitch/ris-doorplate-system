"""
試題 2 - API 設定檔
集中管理資料庫連線設定與 API 基本資訊。
"""
import os

# ── 資料庫設定（從環境變數讀取，地端/Docker 皆適用）────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "db"),
    "port":     int(os.getenv("DB_PORT", "5432")),
    "dbname":   os.getenv("DB_NAME",     "crawldb"),
    "user":     os.getenv("DB_USER",     "admin"),
    "password": os.getenv("DB_PASSWORD", "admin123"),
    "sslmode":  os.getenv("DB_SSLMODE",  "disable"),  # 地端=disable，雲地=require
}

# ── FastAPI 應用程式資訊 ──────────────────────────────────────
API_TITLE       = "門牌資料查詢 API"
API_DESCRIPTION = (
    "查詢內政部戶政司門牌初編資料（台北市，民國 114 年）\n\n"
    "資料由爬蟲寫入 PostgreSQL，本 API 提供查詢介面。\n\n"
    "**異常通知**：查詢結果為空時，自動發送 LINE Notify 通報。"
)
API_VERSION = "1.0.0"
