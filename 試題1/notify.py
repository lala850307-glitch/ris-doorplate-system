"""
Email 異常通知模組
試題 1（爬蟲）與試題 2（API）共用相同介面。

使用方式：
    from notify import send_notify
    send_notify("[🚨 爬蟲異常] 發生錯誤訊息")

環境變數（設定於 .env）：
    MAIL_USER      - 寄件人 Gmail 帳號（例：your@gmail.com）
    MAIL_PASSWORD  - Gmail App Password（16 碼，非 Google 登入密碼）
    MAIL_TO        - 收件人 Email（可與寄件人相同）

注意：
    若以上環境變數未設定，程式不會中斷，
    只會印出 WARNING log，方便在沒有 Email 設定的環境測試。
"""

import logging
import os
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("notify")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_notify(message: str) -> None:
    """
    發送 Email 異常通知。

    Args:
        message: 通知內文，例如：
                 "[🚨 爬蟲異常] 信義區爬取失敗：ConnectionError"
                 "[⚠️ 查詢異常] 台北市大安區 查無資料"

    行為：
        - 環境變數齊全 → 寄出 Email
        - 環境變數缺少 → 只印 WARNING log，不中斷程式
        - 寄送失敗     → 印 ERROR log，不拋出例外
    """
    mail_user = os.getenv("MAIL_USER", "").strip()
    mail_pass = os.getenv("MAIL_PASSWORD", "").strip()
    mail_to   = os.getenv("MAIL_TO", "").strip()

    # 任一設定缺少 → 跳過發送
    if not all([mail_user, mail_pass, mail_to]):
        logger.warning(f"[Email 通知] 環境變數未設定，略過發送。訊息內容：{message}")
        return

    try:
        msg = MIMEText(message, "plain", "utf-8")
        msg["Subject"] = f"[系統通知] {message[:30]}..."
        msg["From"]    = mail_user
        msg["To"]      = mail_to

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(mail_user, mail_pass)
            server.sendmail(mail_user, mail_to, msg.as_string())

        logger.info(f"[Email 通知] 發送成功 → {mail_to}：{message[:40]}...")

    except smtplib.SMTPAuthenticationError:
        logger.error("[Email 通知] 認證失敗，請確認 MAIL_USER / MAIL_PASSWORD 是否正確（需使用 App Password）")
    except smtplib.SMTPException as e:
        logger.error(f"[Email 通知] SMTP 錯誤：{e}")
    except Exception as e:
        logger.error(f"[Email 通知] 未預期錯誤：{e}")
