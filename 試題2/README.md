# 試題 2 - 門牌資料查詢 API

## 說明

基於 FastAPI 開發的 RESTful 查詢服務，查詢試題 1 爬蟲寫入 PostgreSQL 的門牌初編資料。
提供 Swagger UI 互動文件與綠色主題 HTML 查詢介面。

---

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `main.py` | FastAPI 主程式，含路由、middleware、log |
| `models.py` | Pydantic Request / Response 資料模型 |
| `db.py` | PostgreSQL 連線池與查詢函式 |
| `config.py` | API 標題、版本等設定 |
| `notify.py` | Email 異常通知 |
| `static/index.html` | 綠色主題 HTML 查詢介面 |

---

## 執行方式

### Docker 執行（推薦）

從根目錄啟動：

```bash
docker compose up -d
```

API 啟動後可透過以下方式存取：

| 介面 | URL |
|------|-----|
| HTML 查詢介面 | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |

### 本機直接執行

```bash
cd 試題2
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

## API 端點

### `GET /health` — 健康檢查

確認 API 服務與資料庫連線狀態。

```bash
curl http://localhost:8000/health
```

**Response：**
```json
{
  "status": "ok",
  "db": "connected",
  "timestamp": "2026-05-27T14:00:00+00:00"
}
```

---

### `POST /query` — 查詢門牌資料

依縣市和鄉鎮市區查詢門牌初編資料，支援分頁。

```bash
curl -X POST "http://localhost:8000/query?limit=10&offset=0" \
  -H "Content-Type: application/json" \
  -d '{"city": "台北市", "township": "大安區"}'
```

**Request Body：**
```json
{
  "city":     "台北市",
  "township": "大安區"
}
```

**Query Params（可選）：**

| 參數 | 預設 | 說明 |
|------|------|------|
| `limit` | 100 | 每頁筆數（1–1000） |
| `offset` | 0 | 跳過筆數 |

**Response：**
```json
{
  "city":     "台北市",
  "township": "大安區",
  "total":    267,
  "count":    10,
  "limit":    10,
  "offset":   0,
  "data": [
    {
      "city":              "台北市",
      "township":          "大安區",
      "village":           "XX里",
      "address":           "XX路XX號",
      "registration_date": "114/10/01",
      "registration_type": "門牌初編"
    }
  ]
}
```

---

## Log 格式

每次請求自動記錄：

```
2026-05-27 14:00:01 | INFO    | 查詢請求 | city=台北市 township=大安區 limit=100 offset=0
2026-05-27 14:00:01 | INFO    | 查詢完成 | city=台北市 township=大安區 | total=267 count=100 | duration=18ms
2026-05-27 14:00:01 | INFO    | method=POST path=/query status=200 duration=20.1ms
2026-05-27 14:00:05 | WARNING | [⚠️ 查詢異常] 台北市XX區 查無資料，請確認爬蟲是否已執行
```

---

## 異常通知（Email）

| 觸發情境 | 通知內容 |
|---------|---------|
| 查詢結果為空（total=0） | `[⚠️ 查詢異常] {city}{township} 查無資料，請確認爬蟲是否已執行` |
| 資料庫錯誤 | HTTP 500 + ERROR log（不發 Email，直接回錯誤） |

> Email 設定留空時程式仍可正常執行，僅會在 log 印出 WARNING。
