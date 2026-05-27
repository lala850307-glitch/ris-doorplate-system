# 試題 4 - 系統架構圖

## 說明

請參閱 [architecture.md](./architecture.md)，內含三張 Mermaid 架構圖與完整選型說明。

---

## 架構圖清單

### 圖 1：資料流程圖

描述從排程觸發到資料落檔的完整流程：

```
APScheduler（每天 08:00）
    → crawler.py（requests 直打 API）
    → captcha.py（ddddocr 驗證碼辨識）
    → 內政部戶政司後端 API
    → 取得 jqGrid JSON 資料
    → db.py 寫入 PostgreSQL
    → csv_exporter.py 輸出 CSV
    → notify.py 發送 Email 異常通知

FastAPI（api container）
    → 接收 POST /query 請求
    → 查詢 PostgreSQL
    → 回傳 JSON 結果
    → 查無資料時發送 Email 通知
```

### 圖 2：Log 監控流程

```
crawler / api（stdout log）
    → Promtail（Docker socket 收集）
    → Loki（儲存，Port 3100）
    → Grafana（可視化，Port 3000）
```

### 圖 3：Docker Compose 服務關係圖

描述各容器的依賴關係與網路連接方式（app-network bridge）。

---

## 元件選型說明摘要

| 元件 | 選擇 | 理由 |
|------|------|------|
| 爬蟲框架 | requests | 目標網站為後端 API 回傳 JSON，無需瀏覽器，速度快、映像小 |
| API 框架 | FastAPI | ASGI 非同步、自動 Swagger UI、Pydantic 型別驗證 |
| 資料庫 | PostgreSQL | 欄位固定的關聯式資料，支援索引查詢，官方 Docker 映像輕量 |
| Log 收集 | Loki + Promtail | 比 ELK 輕量，Promtail 自動偵測 Docker 容器無需改程式碼 |
| 異常通知 | Email（Gmail SMTP）| 通用、免費，使用 Python 內建 smtplib 無需額外套件 |
| 排程 | APScheduler | 輕量，直接在 Python 程式內定義 cron，不需系統服務 |

---

## 查看方式

- **VS Code**：安裝 `Markdown Preview Mermaid Support` 擴充套件後直接預覽
- **GitLab**：直接開啟 `architecture.md`，Mermaid 圖自動渲染
- **線上工具**：[Mermaid Live Editor](https://mermaid.live/)
