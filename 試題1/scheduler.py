"""
試題 1 - 爬蟲自動排程（加分題）
========================================
使用 APScheduler 設定每天 08:00 自動執行爬蟲

執行方式：
  python scheduler.py

排程設定：
  - 每天 08:00（Asia/Taipei 時區）自動呼叫 crawler.main()
  - 排程啟動、每次觸發、執行結果都記錄到 log
  - 可用 Ctrl+C 安全停止

Docker 使用：
  docker-compose.yml 的 crawler service 預設執行這個檔案
  若要立即執行一次爬蟲，改成：command: python crawler.py
"""

import logging
import sys
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

# ─────────────────────────────────────────────────────────────────
# 重用 crawler.py 的 logger 設定（log 同樣寫到 crawler.log）
# ─────────────────────────────────────────────────────────────────
# 直接 import crawler 模組，setup_logger() 會自動初始化
from main import main as run_crawler, setup_logger

logger = setup_logger()


# ─────────────────────────────────────────────────────────────────
# 排程執行的工作函式
# ─────────────────────────────────────────────────────────────────
def crawl_job() -> None:
    """
    排程觸發時執行的函式
    呼叫 crawler.main() 並記錄執行狀態
    """
    logger.info("=" * 60)
    logger.info("【排程觸發】開始執行定期爬蟲任務")
    logger.info("=" * 60)
    try:
        run_crawler()
        logger.info("【排程完成】爬蟲任務執行成功")
    except Exception as e:
        # 這裡的 Exception 已在 crawler.main() 內部處理過
        # 此處僅做最後一道 log 防護
        logger.error(f"【排程失敗】爬蟲任務發生未預期錯誤：{e}")


# ─────────────────────────────────────────────────────────────────
# APScheduler 事件監聽（記錄每次執行結果到 log）
# ─────────────────────────────────────────────────────────────────
def on_job_executed(event) -> None:
    """排程成功執行後的回呼：記錄 INFO log"""
    logger.info(f"【排程事件】Job '{event.job_id}' 執行完畢")


def on_job_error(event) -> None:
    """排程執行發生例外時的回呼：記錄 ERROR log"""
    logger.error(f"【排程事件】Job '{event.job_id}' 執行發生例外：{event.exception}")


# ─────────────────────────────────────────────────────────────────
# 主程式：建立並啟動排程器
# ─────────────────────────────────────────────────────────────────
def main() -> None:
    """
    建立 BlockingScheduler，設定每天 08:00 執行爬蟲
    程式會持續運行直到 Ctrl+C 中止
    """
    scheduler = BlockingScheduler(timezone="Asia/Taipei")

    # 註冊事件監聽
    scheduler.add_listener(on_job_executed, EVENT_JOB_EXECUTED)
    scheduler.add_listener(on_job_error,    EVENT_JOB_ERROR)

    # 設定排程：每天 08:00（Asia/Taipei）
    scheduler.add_job(
        func=crawl_job,
        trigger=CronTrigger(hour=8, minute=0, timezone="Asia/Taipei"),
        id="daily_crawl",
        name="每日門牌資料爬蟲",
        replace_existing=True,
        misfire_grace_time=600,   # 若系統睡眠導致錯過，10 分鐘內補跑
    )

    logger.info("=" * 60)
    logger.info("排程器已啟動")
    logger.info("執行時間：每天 08:00（Asia/Taipei）")
    logger.info("按 Ctrl+C 可安全停止排程器")
    logger.info("=" * 60)

    # 列出已註冊的排程
    scheduler.print_jobs()

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("收到停止訊號（Ctrl+C），排程器正在關閉...")
        scheduler.shutdown(wait=False)
        logger.info("排程器已停止")


if __name__ == "__main__":
    main()
