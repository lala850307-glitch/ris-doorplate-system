"""
試題 1 - CSV 落檔模組

以 UTF-8-BOM 編碼輸出，確保在 Windows Excel 開啟時不會出現中文亂碼。
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from config import CSV_HEADERS_ZH, OUTPUT_DIR


def write_csv(records: Iterable, filename: str = "result.csv") -> Path:
    """
    將爬取結果寫入 CSV 檔案。

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

    return out_path
