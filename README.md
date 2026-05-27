# RIS 門牌資料爬蟲系統

## 環境需求

- Docker Desktop

---

## 啟動

**步驟 1**：確認根目錄有 `.env` 檔案，填入資料庫與 Email 設定。

**步驟 2**：啟動所有服務

```bash
docker compose up -d
```

**步驟 3**：執行爬蟲

```bash
docker compose up crawler
```

看到 `爬蟲完成｜成功 XXXX 筆｜失敗行政區：無` 即完成。

---

## 服務入口

| 服務 | URL | 帳號 |
|------|-----|------|
| 查詢介面 | http://localhost:8000 | — |
| Swagger UI | http://localhost:8000/docs | — |
| Grafana 監控 | http://localhost:3000 | admin / admin |

---

## 常用指令

```bash
# 查看爬蟲即時 log
docker compose logs -f crawler

# 停止所有服務
docker compose down
```

---

## 各試題

| 試題 | 說明 |
|------|------|
| [試題1](./試題1/README.md) | 門牌資料爬蟲 |
| [試題2](./試題2/README.md) | FastAPI 查詢 API |
| [試題3](./試題3/README.md) | Log 監控（Grafana） |
| [試題4](./試題4/README.md) | 系統架構說明 |
