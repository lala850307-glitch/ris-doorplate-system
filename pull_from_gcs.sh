#!/bin/bash
# ============================================================
# 雲地模式 Pull 腳本
# 從 GCS 下載爬蟲產出的 CSV，匯入地端 PostgreSQL
# 使用方式：bash pull_from_gcs.sh
#       或：make pull
# ============================================================

set -e

BUCKET="ris-doorplate-project-3d70850b"
CSV_FILE="result.csv"
LOCAL_PATH="試題1/output/${CSV_FILE}"

# 讀取 .env.local 的 DB 設定
export $(grep -v '^#' .env.local | xargs)

echo "📥 從 GCS 下載 CSV..."
gcloud storage cp "gs://${BUCKET}/${CSV_FILE}" "${LOCAL_PATH}"

echo "🗄️  匯入地端 PostgreSQL..."
python3 - << EOF
import csv
import psycopg2
import os

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    dbname="${DB_NAME}",
    user="${DB_USER}",
    password="${DB_PASSWORD}"
)
cur = conn.cursor()

with open("${LOCAL_PATH}", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    rows = [
        (r["縣市"], r["鄉鎮市區"], r["村里"], r["門牌地址"], r["編訂日期"], r["編訂類別"])
        for r in reader
    ]

cur.executemany("""
    INSERT INTO door_plate_data
        (city, township, village, address, registration_date, registration_type)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT DO NOTHING
""", rows)

conn.commit()
print(f"✅ 匯入完成，共 {len(rows)} 筆")
conn.close()
EOF

echo "✅ Pull 完成！"
