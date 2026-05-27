"""
試題 1 - 驗證碼辨識模組

辨識策略：
  第一層：ddddocr（自動 OCR，專為中文網站驗證碼訓練）
  備  援：人工目視輸入（OCR 連續失敗時啟用）

設計說明：
  OCR 辨識失敗時回傳空字串，而非直接 raise Exception。
  這樣 crawler.py 可以直接送出空驗證碼 → server 拒絕
  → server 在回應中提供新的 captchaKey → 自動換圖重試。
  比起每次辨識失敗都要重新導航頁面，效率更高。
"""
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger("crawler")

# 只保留英數字（驗證碼字元集）
_CAPTCHA_RE = re.compile(r"[0-9A-Za-z]")


def _clean(raw: str) -> str:
    """清除 OCR 結果中的空白與雜訊，只留英數字。"""
    return "".join(c for c in raw if _CAPTCHA_RE.match(c))


# ── ddddocr 單例（載入一次，避免每次重新初始化）────────────
_ocr_instance = None


def _get_ocr():
    global _ocr_instance
    if _ocr_instance is None:
        import ddddocr
        _ocr_instance = ddddocr.DdddOcr(show_ad=False, beta=False)
    return _ocr_instance


def solve_auto(img_bytes: bytes) -> str:
    """
    使用 ddddocr 自動辨識驗證碼。

    - 辨識成功且 ≥ 4 碼 → 回傳辨識結果
    - 辨識失敗 / 不足 4 碼 → 回傳空字串，讓 crawler 換圖重試
    """
    try:
        ocr     = _get_ocr()
        raw     = ocr.classification(img_bytes)
        cleaned = _clean(str(raw))
        if len(cleaned) >= 4:
            logger.info(f"  [OCR-ddddocr] {cleaned!r}")
            return cleaned
        logger.debug(f"  [OCR-ddddocr] 結果 {cleaned!r} 不足 4 碼，放棄")
        return ""
    except Exception as e:
        logger.debug(f"  [OCR-ddddocr] 辨識失敗：{e}")
        return ""


def solve_manual(img_path: Path) -> str:
    """
    人工目視輸入驗證碼（OCR 連續失敗時的備援）。

    - macOS：自動用系統預覽程式開啟圖檔
    - 其他平台：印出圖檔路徑，請使用者自行開啟
    """
    print(f"\n[驗證碼] 圖檔位置：{img_path}")
    try:
        import subprocess
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(img_path)])
    except Exception:
        pass

    while True:
        text = input("請輸入圖中驗證碼（按 Enter 送出，輸入 q 取消）: ").strip()
        if text.lower() == "q":
            raise KeyboardInterrupt("使用者取消驗證碼輸入")
        if text:
            return text
