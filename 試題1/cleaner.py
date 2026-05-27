"""
試題 1 - 資料清洗模組（pandas）

清洗爬取的原始資料，確保寫入 CSV 與資料庫前格式一致：

1. 去除所有欄位的前後空白
2. 全形數字轉半形（門牌地址常見：４８６號 → 486號）
3. 編訂日期格式統一（民國114年10月29日 → 114/10/29）
4. 過濾空白記錄（地址為空的資料列）
5. 去除完全重複的資料列
"""
from __future__ import annotations

import logging
import re

import pandas as pd

logger = logging.getLogger("crawler")

# 全形數字 ０～９ → 半形 0～9
_FULLWIDTH_TABLE = str.maketrans("０１２３４５６７８９", "0123456789")


def _to_halfwidth(text: str) -> str:
    """全形數字轉半形。"""
    return text.translate(_FULLWIDTH_TABLE)


def _normalize_date(date_str: str) -> str:
    """
    編訂日期格式統一。

    民國114年10月29日 → 114/10/29
    114/10/29         → 114/10/29（已是標準格式）
    """
    if re.match(r"^\d{2,3}/\d{1,2}/\d{1,2}$", date_str):
        return date_str
    m = re.match(r"民國(\d+)年(\d+)月(\d+)日", date_str)
    if m:
        y, mo, d = m.group(1), m.group(2).zfill(2), m.group(3).zfill(2)
        return f"{y}/{mo}/{d}"
    return date_str  # 無法解析：原樣保留


def clean_records(records: list) -> list:
    """
    使用 pandas 批次清洗 Record 列表。

    清洗步驟：
        1. 轉成 DataFrame
        2. 去除所有欄位前後空白
        3. 門牌地址全形數字轉半形
        4. 編訂日期格式統一
        5. 過濾門牌地址為空的列
        6. 去除重複列

    Returns:
        清洗後的 Record 列表
    """
    if not records:
        return []

    before = len(records)

    # 1. 轉成 DataFrame
    df = pd.DataFrame([{
        "city":              r.city,
        "township":          r.township,
        "village":           r.village,
        "address":           r.address,
        "registration_date": r.registration_date,
        "registration_type": r.registration_type,
    } for r in records])

    # 2. 去除所有欄位前後空白
    df = df.apply(lambda col: col.str.strip() if col.dtype == "object" else col)

    # 3. 門牌地址全形數字 → 半形
    df["address"] = df["address"].apply(_to_halfwidth)

    # 4. 編訂日期格式統一
    df["registration_date"] = df["registration_date"].apply(_normalize_date)

    # 5. 過濾門牌地址為空的列
    df = df[df["address"] != ""]

    # 6. 去除完全重複的資料列
    df = df.drop_duplicates()

    after = len(df)
    dropped = before - after

    if dropped:
        logger.warning(f"[清洗] 過濾 {dropped} 筆（空白或重複），保留 {after} 筆")
    else:
        logger.info(f"[清洗] 完成，共 {after} 筆，格式已統一")

    # 轉回 Record 物件列表
    from crawler import Record
    return [
        Record(
            city=row["city"],
            township=row["township"],
            village=row["village"],
            address=row["address"],
            registration_date=row["registration_date"],
            registration_type=row["registration_type"],
        )
        for _, row in df.iterrows()
    ]
