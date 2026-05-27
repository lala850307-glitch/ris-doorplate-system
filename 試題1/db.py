"""
試題 1 - 資料庫操作層（PostgreSQL）

對外提供四個函式：
    init_db()                    → 建立資料表（若不存在則自動建立）
    save_records(records)        → 批次寫入爬取結果，回傳寫入筆數
    log_start(district)          → 新增 RUNNING 狀態爬蟲紀錄，回傳 log_id
    log_finish(log_id, **kwargs) → 更新爬蟲執行結果（SUCCESS / FAILED）
"""
from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterable

import psycopg2

from config import DB_CONFIG

logger = logging.getLogger("crawler")

# ── SQL 定義 ──────────────────────────────────────────────────
_CREATE_DATA_TABLE = """
CREATE TABLE IF NOT EXISTS door_plate_data (
    id                SERIAL      PRIMARY KEY,
    city              VARCHAR(20) NOT NULL,
    township          VARCHAR(20) NOT NULL,
    village           VARCHAR(30),
    address           TEXT        NOT NULL,
    registration_date VARCHAR(20),
    registration_type VARCHAR(20),
    created_at        TIMESTAMP   DEFAULT NOW(),
    UNIQUE (city, township, address, registration_date)
);
"""

_CREATE_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS crawl_log (
    id            SERIAL      PRIMARY KEY,
    started_at    TIMESTAMP   NOT NULL DEFAULT NOW(),
    finished_at   TIMESTAMP,
    district      VARCHAR(20) NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'RUNNING',
    record_count  INTEGER     NOT NULL DEFAULT 0,
    error_message TEXT
);
"""

_INSERT_SQL = """
INSERT INTO door_plate_data
    (city, township, village, address, registration_date, registration_type)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (city, township, address, registration_date) DO NOTHING
"""


# ── 連線管理 ──────────────────────────────────────────────────
@contextmanager
def _conn():
    """Context manager：自動 commit / rollback / close。"""
    conn = psycopg2.connect(**DB_CONFIG)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Public API ────────────────────────────────────────────────
def init_db() -> None:
    """建立所需資料表（若已存在則略過）。"""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_CREATE_DATA_TABLE)
            cur.execute(_CREATE_LOG_TABLE)
    logger.info("資料庫初始化完成（door_plate_data, crawl_log table 就緒）")


def save_records(records: Iterable) -> int:
    """
    批次寫入門牌資料，重複資料自動跳過（ON CONFLICT DO NOTHING）。
    回傳實際新增筆數。
    """
    rows = list(records)
    if not rows:
        return 0
    inserted = 0
    with _conn() as conn:
        with conn.cursor() as cur:
            for r in rows:
                cur.execute(_INSERT_SQL, (
                    r.city,
                    r.township,
                    r.village,
                    r.address,
                    r.registration_date,
                    r.registration_type,
                ))
                inserted += cur.rowcount  # rowcount=0 代表重複跳過
    return inserted


def log_start(district: str) -> int:
    """
    新增一筆 RUNNING 狀態的爬蟲執行紀錄。
    回傳 log_id，供後續 log_finish() 更新使用。
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO crawl_log (district, status) "
                "VALUES (%s, 'RUNNING') RETURNING id",
                (district,),
            )
            return cur.fetchone()[0]


def log_finish(
    log_id: int,
    *,
    status: str,
    record_count: int = 0,
    error: str | None = None,
) -> None:
    """更新爬蟲執行結果（completed_at、status、record_count、error_message）。"""
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE crawl_log
                SET finished_at   = NOW(),
                    status        = %s,
                    record_count  = %s,
                    error_message = %s
                WHERE id = %s
                """,
                (status, record_count, error, log_id),
            )
