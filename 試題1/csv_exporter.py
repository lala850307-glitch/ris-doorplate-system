"""
試題 1 - CSV 落檔模組

以 UTF-8-BOM 編碼輸出，確保在 Windows Excel 開啟時不會出現中文亂碼。
若設定了 GCS_BUCKET 環境變數，會在本機儲存後自動上傳至 GCS（雲地模式）。
"""
from __future__ import annotations

import csv
import logging
import os
from pathlib import Path
from typing import Iterable

from config import CSV_HEADERS_ZH, OUTPUT_DIR

logger = logging.getLogger("crawler")


def write_csv(records: Iterable, filename: str = "result.csv") -> Path:
    """
    將爬取結果寫入 CSV 檔案，並在雲地模式下上傳至 GCS。

    Args:
        records:  Record 物件的可迭代集合
        filename: 輸出檔名（預設 result.csv，覆蓋式寫入）

    Returns:
        完整的輸出檔案路徑
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / filename

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADERS_ZH)  # 中文欄位標題列
        for r in records:
            writer.writerow([
                r.city,
                r.township,
                r.village,
                r.address,
                r.registration_date,
                r.registration_type,
            ])

    # ── 雲地模式：上傳 CSV 至 GCS ────────────────────────────
    bucket_name = os.getenv("GCS_BUCKET", "").strip()
    if bucket_name:
        _upload_to_gcs(out_path, bucket_name, filename)

    return out_path


def _upload_to_gcs(local_path: Path, bucket_name: str, blob_name: str) -> None:
    """將 CSV 上傳至 GCS Bucket（地端模式不會呼叫此函式）"""
    try:
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(local_path))
        logger.info(f"✅ CSV 已上傳至 GCS：gs://{bucket_name}/{blob_name}")
    except Exception as e:
        logger.warning(f"⚠️ GCS 上傳失敗（不影響本機 CSV）：{e}")
