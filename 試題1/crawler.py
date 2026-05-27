"""
試題 1 - 爬蟲核心

【技術選型說明】
  選用 requests 而非 Selenium，原因：
  透過 Chrome DevTools → Network → XHR 分析，發現網站的查詢結果
  是透過 AJAX 呼叫後端 API 取得的 JSON，並非純 HTML 渲染。
  因此可以直接用 requests 模擬相同的 HTTP 請求，完全不需要瀏覽器。

  優點：
  - 速度更快（省去瀏覽器啟動 / 頁面渲染時間）
  - 部署更簡單（不需安裝 Chrome / ChromeDriver）
  - 更穩定（不受前端 JS 執行時序影響）

【查詢流程（分析自 Network XHR）】
  1. GET  /info-doorplate/app/doorplate/main
         → 取得初始 CSRF token（hidden input）
  2. POST /info-doorplate/app/doorplate/map       searchType=date
         → 取得第二個 CSRF token
  3. POST /info-doorplate/app/doorplate/query     cityCode=63000000
         → 取得查詢頁，含 captchaKey 與最終 CSRF token
  4. GET  /info-doorplate/captcha/image?CAPTCHA_KEY=<key>
         → 下載驗證碼圖片
  5. POST /info-doorplate/app/doorplate/inquiry/date
         → 帶入所有條件 + 驗證碼，回傳 jqGrid JSON 格式資料
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime

import requests
from bs4 import BeautifulSoup

import captcha as captcha_mod
from config import (
    CAPTCHA_DIR, CAPTCHA_URL, CATEGORY, CITY_CODE,
    INQUIRY_URL, MAIN_URL, MAP_URL, MAX_CAPTCHA_RETRY,
    MAX_RETRY, PORTAL_URL, QUERY_URL, REGISTER_KIND,
    REQUEST_TIMEOUT, START_DATE, END_DATE, TARGET_CITY, USER_AGENT,
)

logger = logging.getLogger("crawler")


# ─────────────────────────────────────────────────────────────
# 資料結構
# ─────────────────────────────────────────────────────────────
@dataclass
class Record:
    """單筆門牌編訂記錄。"""
    city:              str
    township:          str
    village:           str
    address:           str
    registration_date: str
    registration_type: str = field(default=CATEGORY)


class CrawlError(Exception):
    """爬蟲執行期間的可預期錯誤。"""


# ─────────────────────────────────────────────────────────────
# 爬蟲主體
# ─────────────────────────────────────────────────────────────
class DoorplateCrawler:
    """
    使用 requests.Session 直接呼叫內政部戶政司 API 的爬蟲。

    Session 維持 cookie，模擬完整瀏覽器 session。
    驗證碼採一次性設計：每次查詢前必須重新取得 captchaKey。
    """

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent":      USER_AGENT,
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        })
        self._csrf:        str | None = None
        self._captcha_key: str | None = None

    # ── HTTP 工具 ──────────────────────────────────────────────
    def _request(self, method: str, url: str, **kw) -> requests.Response:
        """
        帶指數退避 retry 的 HTTP 呼叫。
        伺服器 5xx 或網路錯誤時自動重試 MAX_RETRY 次。
        """
        last_exc: Exception | None = None
        for attempt in range(1, MAX_RETRY + 1):
            try:
                resp = self.session.request(
                    method, url, timeout=REQUEST_TIMEOUT, **kw
                )
                resp.raise_for_status()
                return resp
            except requests.RequestException as exc:
                last_exc = exc
                wait = 5 * attempt
                logger.warning(
                    f"請求失敗（{method} {url}）"
                    f"第 {attempt}/{MAX_RETRY} 次，{wait}s 後重試：{exc}"
                )
                time.sleep(wait)
        raise CrawlError(f"請求 {url} 超過重試上限") from last_exc

    @staticmethod
    def _extract_csrf(html: str) -> str:
        """從 HTML 取出 CSRF token（hidden input 或 meta tag）。"""
        m = re.search(r'name="_csrf"\s+value="([^"]+)"', html)
        if m:
            return m.group(1)
        m = re.search(r'name="_csrf"\s+content="([^"]+)"', html)
        if not m:
            raise CrawlError("找不到 CSRF token")
        return m.group(1)

    # ── Session 初始化 ────────────────────────────────────────
    def open_query_form(self) -> None:
        """
        三步驟建立 session，取得本次查詢用的 CSRF token 與 captchaKey。

        為什麼每次查詢都要重新走這三步？
        → 網站的驗證碼是「一次性」的，成功提交後 captchaKey 立即失效。
          舊 key 無法重複使用，必須重新取得新的 key。
        """
        logger.debug("Step 1/3: GET main")
        r1   = self._request("GET", MAIN_URL, headers={"Referer": PORTAL_URL})
        csrf = self._extract_csrf(r1.text)

        logger.debug("Step 2/3: POST map (searchType=date)")
        r2   = self._request(
            "POST", MAP_URL,
            data={"searchType": "date", "_csrf": csrf},
            headers={"Referer": MAIN_URL},
        )
        csrf = self._extract_csrf(r2.text)

        logger.debug("Step 3/3: POST query (cityCode=%s)", CITY_CODE)
        r3   = self._request(
            "POST", QUERY_URL,
            data={"searchType": "date", "cityCode": CITY_CODE, "_csrf": csrf},
            headers={"Referer": MAP_URL},
        )

        soup = BeautifulSoup(r3.text, "html.parser")

        csrf_input = soup.find("input", attrs={"name": "_csrf"})
        if not csrf_input:
            raise CrawlError("查詢頁找不到 CSRF token")
        self._csrf = csrf_input["value"]

        key_input = soup.find("input", attrs={"name": "captchaKey"})
        if not key_input or not key_input.get("value"):
            raise CrawlError("查詢頁找不到 captchaKey")
        self._captcha_key = key_input["value"]
        logger.debug(f"query form 就緒，captchaKey={self._captcha_key[:8]}...")

    # ── 驗證碼下載 ────────────────────────────────────────────
    def _fetch_captcha(self) -> tuple[bytes, object]:
        """
        下載驗證碼圖片。

        為什麼不直接用 urllib？
        → 驗證碼圖片 URL 需要 session cookie 才能取得，
          requests.Session 天然持有 cookie，不需額外處理。
        """
        assert self._captcha_key
        r = self._request(
            "GET", CAPTCHA_URL,
            params={
                "CAPTCHA_KEY": self._captcha_key,
                "time":        str(int(time.time() * 1000)),
            },
            headers={"Referer": QUERY_URL},
        )
        CAPTCHA_DIR.mkdir(parents=True, exist_ok=True)
        stamp    = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        img_path = CAPTCHA_DIR / f"captcha_{stamp}.jpg"
        img_path.write_bytes(r.content)
        logger.debug(f"驗證碼圖已存：{img_path}（{len(r.content)} bytes）")
        return r.content, img_path

    # ── 查詢單一行政區 ────────────────────────────────────────
    def query_district(self, district: str, area_code: str) -> list[Record]:
        """
        查詢單一行政區的門牌初編資料。

        驗證碼 retry 邏輯：
        - 前 (MAX_CAPTCHA_RETRY - 2) 次：ddddocr 自動辨識
        - 最後 2 次：切換人工輸入（確保一定能過）
        - 若 server 在錯誤回應中附上新 captchaKey → 直接採用，不需重新走三步流程
        """
        self.open_query_form()

        for attempt in range(1, MAX_CAPTCHA_RETRY + 1):
            logger.info(f"[{district}] 驗證碼嘗試 {attempt}/{MAX_CAPTCHA_RETRY}")

            img_bytes, img_path = self._fetch_captcha()

            if attempt <= MAX_CAPTCHA_RETRY - 2:
                captcha_text = captcha_mod.solve_auto(img_bytes)
            else:
                logger.warning(f"[{district}] OCR 多次失敗，切換人工輸入")
                captcha_text = captcha_mod.solve_manual(img_path)

            payload = {
                "searchType":     "date",
                "cityCode":       CITY_CODE,
                "tkt":            "-1",
                "areaCode":       area_code,
                "registerKind":   REGISTER_KIND,
                "village":        "",
                "neighbor":       "",
                "sDate":          START_DATE,
                "eDate":          END_DATE,
                "_includeNoDate": "on",
                "captchaInput":   captcha_text,
                "captchaKey":     self._captcha_key,
                "_csrf":          self._csrf,
                # jqGrid 分頁參數（一次取最多 1000 筆）
                "_search": "false",
                "rows":    "1000",
                "page":    "1",
                "sidx":    "",
                "sord":    "asc",
            }

            logger.info(
                f"[{district}] POST inquiry "
                f"areaCode={area_code} captcha={captcha_text!r}"
            )
            r = self._request(
                "POST", INQUIRY_URL,
                data=payload,
                headers={
                    "Referer":          QUERY_URL,
                    "X-Requested-With": "XMLHttpRequest",  # 告知 server 這是 AJAX 請求
                },
            )

            try:
                data = r.json()
            except ValueError:
                raise CrawlError(f"API 回傳非 JSON：{r.text[:200]}")

            # ── 解析 errorMsg ──────────────────────────────────
            # 重要細節：server 回應中即使有 errorMsg，不一定代表失敗。
            # errorMsg 分兩種情況：
            #   真錯誤 → 含 title / msg / error:true → 需處理
            #   輪替資訊 → 只含 captcha / token → 是給「下次」用的，本次成功
            err_obj: dict = {}
            err = data.get("errorMsg")
            if err:
                if isinstance(err, str):
                    try:
                        err_obj = json.loads(err)
                    except ValueError:
                        err_obj = {"title": err}
                elif isinstance(err, dict):
                    err_obj = err

            title         = str(err_obj.get("title", ""))
            msg           = str(err_obj.get("msg",   ""))
            is_real_error = bool(title or msg or err_obj.get("error"))

            if is_real_error:
                # 「查無資料」是正常查詢結果，代表該區在指定條件下沒有資料
                # 不應視為錯誤，直接回傳空列表
                no_data_keywords = ["查無資料", "沒有符合", "查無符合"]
                if any(kw in title or kw in msg for kw in no_data_keywords):
                    logger.info(
                        f"[{district}] 查無資料"
                        f"（該區在指定日期內無門牌初編記錄）"
                    )
                    return []

                is_captcha_err = (
                    "驗證" in title or "驗證" in msg
                    or "captcha" in (title + msg).lower()
                )
                if is_captcha_err:
                    # server 有時直接在 errorMsg.captcha 給新的 key，直接用
                    new_key = err_obj.get("captcha")
                    if new_key:
                        logger.debug(
                            f"  server 給新 captchaKey={str(new_key)[:8]}..."
                        )
                        self._captcha_key = str(new_key)
                    logger.warning(
                        f"[{district}] 驗證碼錯誤（{title or msg}），重試"
                    )
                    continue
                raise CrawlError(f"server 錯誤：{title or msg}")

            # 沒有真錯誤 → 本次查詢成功，解析結果
            return list(self._parse_rows(data, district))

        raise CrawlError(
            f"[{district}] 驗證碼嘗試 {MAX_CAPTCHA_RETRY} 次均失敗"
        )

    # ── 資料解析 ──────────────────────────────────────────────
    @staticmethod
    def _parse_rows(data: dict, district: str) -> list[Record]:
        """
        解析 jqGrid JSON 格式的查詢結果。

        jqGrid 回應有兩種結構：
          格式 A：{ "rows": [{ "cell": [v1, v2, v3] }, ...] }
          格式 B：{ "rows": [{ "v1": ..., "v2": ..., "v3": ... }, ...] }
        兩種都相容。
        """
        rows = data.get("rows") or []
        logger.info(
            f"[{district}] 取得 {len(rows)} 筆"
            f"（total={data.get('records')} page={data.get('page')}）"
        )

        records = []
        for row in rows:
            if "cell" in row and isinstance(row["cell"], list):
                cell = row["cell"]
                v1   = cell[0] if len(cell) > 0 else ""
                v2   = cell[1] if len(cell) > 1 else ""
            else:
                v1 = row.get("v1", "")
                v2 = row.get("v2", "")

            full_addr = str(v1).strip()

            # 從完整門牌地址擷取村里（例：「信義里」「富台里」）
            village = ""
            m = re.search(r"[一-鿿]{1,4}[里村]", full_addr)
            if m:
                village = m.group(0)

            records.append(Record(
                city=TARGET_CITY,
                township=district,
                village=village,
                address=full_addr,
                registration_date=str(v2).strip(),
            ))

        return records
