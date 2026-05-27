"""
試題 1 - 爬蟲進入點

執行方式：
    # 單次執行（預設，遇到 OCR 失敗會自動切換人工輸入）
    python main.py

    # 或透過排程器持續執行（每天 08:00 自動觸發）
    python scheduler.py
"""
from __future__ import annotations

import logging
import shutil
import sys
import traceback

from dotenv import load_dotenv

load_dotenv()  # 讀取 .env 環境變數（DB_HOST、LINE_NOTIFY_TOKEN 等）

from config import CAPTCHA_DIR, CATEGORY, END_DATE, LOG_DIR, START_DATE, TAIPEI_DISTRICTS, TARGET_CITY
from crawler import CrawlError, DoorplateCrawler
from csv_exporter import write_csv
from cleaner import clean_records
from db import init_db, log_finish, log_start, save_records
from notify import send_notify


# ─────────────────────────────────────────────────────────────
# Logger 設定
# ─────────────────────────────────────────────────────────────
def setup_logger() -> logging.Logger:
    """
    建立 crawler logger。
    - stdout：即時顯示（Promtail 從 Docker stdout 收集）
    - 檔案：寫入 logs/crawler.log（同時保留本機紀錄）
    """
    logger = logging.getLogger("crawler")
    if logger.handlers:
        return logger  # 避免重複加入 handler（scheduler 多次呼叫時）

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 檔案 handler
    fh = logging.FileHandler(LOG_DIR / "crawler.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # stdout handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


logger = setup_logger()


# ─────────────────────────────────────────────────────────────
# 主程式
# ─────────────────────────────────────────────────────────────
def main() -> None:
    # 清空舊驗證碼圖片（每次執行前重置，保持資料夾乾淨）
    shutil.rmtree(CAPTCHA_DIR, ignore_errors=True)
    logger.info("已清空舊驗證碼圖片")

    logger.info("=" * 64)
    logger.info("開始執行門牌資料爬蟲")
    logger.info(f"目標：{TARGET_CITY} 各行政區（共 {len(TAIPEI_DISTRICTS)} 區）")
    logger.info(f"日期：{START_DATE} ～ {END_DATE}")
    logger.info(f"類別：{CATEGORY}")
    logger.info("=" * 64)

    # 資料庫初始化
    try:
        init_db()
    except Exception as e:
        logger.critical(f"資料庫初始化失敗，程式中止：{e}")
        send_notify(f"[🚨 爬蟲異常] 資料庫連線失敗：{e}")
        return

    crawler          = DoorplateCrawler()
    all_records:      list = []
    failed_districts: list[str] = []

    for district, area_code in TAIPEI_DISTRICTS.items():
        logger.info(f"── 開始爬取：{TARGET_CITY} {district}")
        log_id = log_start(district)

        try:
            records = crawler.query_district(district, area_code)

            # 資料清洗（去空白、全形轉半形、日期格式統一、去重）
            records = clean_records(records)
            all_records.extend(records)

            # 每區完成立即寫入 DB（中途失敗也能保留已完成的資料）
            saved = save_records(records)
            logger.info(f"✓ {district} 完成，爬取 {len(records)} 筆，寫入 {saved} 筆")
            log_finish(log_id, status="SUCCESS", record_count=len(records))

        except KeyboardInterrupt:
            log_finish(log_id, status="CANCELLED", error="使用者取消")
            logger.warning("使用者取消，停止爬取")
            break

        except Exception as e:
            logger.error(f"✗ {district} 爬取失敗：{e}\n{traceback.format_exc()}")
            log_finish(log_id, status="FAILED", error=str(e))
            failed_districts.append(district)
            send_notify(f"[🚨 爬蟲異常] {district} 爬取失敗：{e}")

    # CSV 落檔
    if all_records:
        csv_path = write_csv(all_records)
        logger.info(f"CSV 已儲存：{csv_path}（共 {len(all_records)} 筆）")
    else:
        logger.warning("本次爬蟲未取得任何資料")
        send_notify("[⚠️ 爬蟲警告] 本次爬蟲未取得任何資料，請確認網站是否異常")

    logger.info("=" * 64)
    logger.info(
        f"爬蟲完成｜成功 {len(all_records)} 筆｜"
        f"失敗行政區：{', '.join(failed_districts) if failed_districts else '無'}"
    )
    logger.info("=" * 64)

    if failed_districts:
        send_notify(
            f"[🚨 爬蟲異常] 以下行政區爬取失敗：\n{', '.join(failed_districts)}"
        )


if __name__ == "__main__":
    main()
