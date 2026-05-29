# RIS 門牌資料爬蟲系統

## 各試題說明

### 試題 1 — 門牌資料爬蟲 → [詳細說明](./試題1/README.md)

爬取內政部戶政司網站，擷取台北市 12 個行政區的門牌初編資料（民國 114/09/01 ～ 114/11/30）。
使用 requests 直接呼叫後端 API（不使用 Selenium），ddddocr 自動辨識驗證碼，失敗時切換人工輸入。
資料清洗後寫入 PostgreSQL，同步輸出 CSV，APScheduler 每天 08:00 自動執行。

### 試題 2 — FastAPI 查詢 API → [詳細說明](./試題2/README.md)

提供 `POST /query` 介面，依縣市與行政區查詢門牌資料。
內建 Swagger UI（`/docs`）與靜態查詢頁面（`/`），查詢結果為空時自動寄送 Email 通知。

### 試題 3 — Log 監控 → [詳細說明](./試題3/README.md)

使用 Grafana + Loki + Promtail 收集爬蟲與 API 的執行紀錄。
`make local` 啟動後儀表板自動就緒，無需手動設定，支援歷史紀錄查詢。

### 試題 4 — 系統架構圖 → [詳細說明](./試題4/README.md)

包含全地端架構（`make local`）與雲地並行架構（GCP VM 爬取 + 地端 DB）兩種設計。
雲地架構採 GCS Pull Model，資料庫永遠在地端，符合金管會對資料不出境的規範。

---

## 環境需求

- Docker Desktop（需先啟動）

---

## 啟動步驟

**步驟 1**：建立環境設定檔

**macOS / Linux：**
```bash
cp .env.example .env
```

**Windows：**
```bat
copy .env.example .env
```

`.env` 預設值即可直接使用，若需要 Email 異常通知，請填入 `MAIL_USER`、`MAIL_PASSWORD`、`MAIL_TO`。

---

**步驟 2**：一鍵啟動所有服務

**macOS / Linux：**
```bash
make local
```

**Windows（不需安裝 Make，直接執行）：**
```bat
start.bat
```
或在檔案總管中直接雙擊 `start.bat`。

啟動後會自動開啟：
- 查詢介面 / Swagger UI → http://localhost:8000/docs
- Grafana 監控儀表板 → http://localhost:3000（帳號 admin / 密碼 admin）

---

**步驟 3**：執行爬蟲（資料擷取）

**macOS / Linux：**
```bash
make crawl
```

**Windows：**
```bat
docker compose up crawler
```

爬蟲為一次性任務，執行完畢後容器自動停止。
看到 `爬蟲完成｜成功 XXXX 筆｜失敗行政區：無` 即完成。

---

## 服務入口

| 服務 | URL | 說明 |
|------|-----|------|
| 查詢介面 | http://localhost:8000 | 視覺化查詢頁面 |
| Swagger UI | http://localhost:8000/docs | API 互動測試介面 |
| Grafana 監控 | http://localhost:3000 | 帳號 admin / 密碼 admin |

---

## 常用指令

| 動作 | macOS / Linux | Windows |
|------|--------------|---------|
| 查看爬蟲 log | `make logs` | `docker compose logs -f crawler` |
| 停止所有服務 | `make stop` | `docker compose down` |
