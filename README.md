# RIS 門牌資料爬蟲系統

## 環境需求

- Docker Desktop（需先啟動）
- Make（macOS 內建，Windows 需另行安裝）

---

## 啟動步驟

**步驟 1**：建立環境設定檔

```bash
cp .env.example .env
```

`.env` 預設值即可直接使用，若需要 Email 異常通知，請填入 `MAIL_USER`、`MAIL_PASSWORD`、`MAIL_TO`。

**步驟 2**：一鍵啟動所有服務

```bash
make local
```

啟動後會自動開啟：
- 查詢介面 / Swagger UI → http://localhost:8000/docs
- Grafana 監控儀表板 → http://localhost:3000（帳號 admin / 密碼 admin）

**步驟 3**：執行爬蟲（資料擷取）

```bash
make crawl
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

```bash
# 查看爬蟲即時 log
make logs

# 停止所有服務
make stop
```

---

## 各試題說明

| 試題 | 說明 |
|------|------|
| [試題1](./試題1/README.md) | 門牌資料爬蟲 |
| [試題2](./試題2/README.md) | FastAPI 查詢 API |
| [試題3](./試題3/README.md) | Log 監控（Grafana） |
| [試題4](./試題4/README.md) | 系統架構說明 |
