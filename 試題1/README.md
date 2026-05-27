# 試題 1 - 內政部戶政司門牌資料爬蟲

## 說明

爬取 [內政部戶政司](https://www.ris.gov.tw/app/portal/3053) 台北市各行政區的門牌初編資料。

| 查詢條件 | 值 |
|---------|-----|
| 縣市 | 台北市（全部 12 個行政區） |
| 編訂日期 | 民國 114/09/01 ～ 114/11/30 |
| 編訂類別 | 門牌初編 |

---

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `crawler.py` | 爬蟲主程式，使用 requests 直打後端 API |
| `main.py` | 進入點，負責 Logger、流程控制、CSV 落檔 |
| `scheduler.py` | 排程版（加分題），每天 08:00 自動觸發 |
| `captcha.py` | 驗證碼辨識，ddddocr 多模型投票 |
| `config.py` | 查詢條件、URL、台北市 12 區代碼 |
| `db.py` | PostgreSQL 建表、寫入、執行記錄 |
| `csv_exporter.py` | 輸出 `output/result.csv` |
| `cleaner.py` | 資料清洗（pandas，全形轉半形、日期格式統一、去重） |
| `notify.py` | Email 異常通知（可選） |
| `output/result.csv` | 爬蟲輸出（執行後產生） |
| `logs/crawler.log` | 執行 log（執行後產生） |

---

## 執行方式

### Docker 執行（推薦）

從根目錄一鍵啟動，爬蟲會自動執行：

```bash
docker compose up -d
```

或單獨執行爬蟲：

```bash
docker compose up crawler
```

### 查看即時 log

```bash
docker compose logs -f crawler
```

---

## 爬蟲設計說明

### 為何選用 requests（而非 Selenium / Scrapy）

透過 Chrome DevTools → Network → XHR 分析，發現查詢結果是由後端 `/inquiry/date` API 直接回傳 JSON（jqGrid 格式），並非 JavaScript 動態渲染的 HTML。

因此直接用 `requests` 模擬 HTTP 請求即可，無需啟動瀏覽器。

| 優點 | 說明 |
|------|------|
| 速度快 | 省去瀏覽器啟動與頁面渲染時間 |
| 部署簡單 | Docker 映像不需安裝 Chrome，從 ~500MB 縮至 ~150MB |
| 穩定 | 不受前端 JS 執行時序影響 |
| Session 管理 | `requests.Session` 自動維持 cookie，確保 CSRF token 有效 |

### 爬蟲流程（三步驟建立 session）

```
GET  /info-doorplate/app/doorplate/main       → 取得 CSRF token
POST /info-doorplate/app/doorplate/map        → 取得第二個 CSRF token
POST /info-doorplate/app/doorplate/query      → 取得 captchaKey
GET  /info-doorplate/captcha/image?CAPTCHA_KEY=<key> → 下載驗證碼圖片
POST /info-doorplate/app/doorplate/inquiry/date       → 查詢結果（jqGrid JSON）
```

### 驗證碼辨識策略

```
ddddocr 多模型投票（最多 8 次）
    ↓ 若失敗
回傳空字串讓 server 自動換圖重試
    ↓ 最後 2 次
人工輸入（互動模式）
```

---

## 輸出結果

### CSV 檔案（`output/result.csv`）

| 欄位 | 說明 |
|------|------|
| `city` | 縣市（台北市） |
| `township` | 鄉鎮市區 |
| `village` | 村里 |
| `address` | 門牌號碼 |
| `registration_date` | 編訂日期（民國） |
| `registration_type` | 編訂類別 |

### PostgreSQL（`door_plate_data` table）

```sql
-- 查看資料
SELECT * FROM door_plate_data LIMIT 10;

-- 查看各行政區筆數
SELECT township, COUNT(*) FROM door_plate_data GROUP BY township ORDER BY township;
```

---

## Log 格式

```
2026-05-27 14:00:01 | INFO    | 開始執行門牌資料爬蟲
2026-05-27 14:00:05 | INFO    | ── 開始爬取：台北市 大安區
2026-05-27 14:02:18 | INFO    | ✓ 大安區 完成，爬取 267 筆，寫入 267 筆
2026-05-27 14:03:10 | WARNING | 驗證碼辨識失敗，重試中...
2026-05-27 14:30:00 | INFO    | 爬蟲完成｜成功 3187 筆｜失敗行政區：無
```

---

## 異常通知（Email）

以下情況會自動發送 Email 通知：

| 觸發情境 | 通知內容 |
|---------|---------|
| 資料庫連線失敗 | `[🚨 爬蟲異常] 資料庫連線失敗：...` |
| 某行政區爬取失敗 | `[🚨 爬蟲異常] 大安區 爬取失敗：...` |
| 本次完全無資料 | `[⚠️ 爬蟲警告] 本次爬蟲未取得任何資料` |
| 最終有失敗行政區 | `[🚨 爬蟲異常] 以下行政區爬取失敗：信義區, ...` |

> Email 設定留空時程式仍可正常執行，僅會在 log 印出 WARNING。
