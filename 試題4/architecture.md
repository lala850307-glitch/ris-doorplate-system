# 試題 4 - 系統架構圖

---

## 圖 1：資料流程圖

```mermaid
flowchart TD
    subgraph 排程層
        SCH["排程器\n每天 08:00 自動觸發爬蟲"]
    end

    subgraph 爬蟲層
        CFG["設定檔\n管理網址與查詢條件"]
        CAP["驗證碼辨識\n自動辨識，失敗時切換人工輸入"]
        CRW["爬蟲主體\n模擬瀏覽器請求，直接呼叫後端 API"]
        DB1["資料庫模組\n負責寫入與查詢資料庫"]
        CSV["CSV 輸出模組\n將資料輸出成 CSV 檔案"]
        MAIN["主程式\n控制爬取流程，記錄執行紀錄"]
    end

    subgraph 外部資源
        WEB["內政部戶政司網站\n門牌資料查詢 API"]
    end

    subgraph 儲存層
        CSVF["輸出的 CSV 檔案"]
        PG[("資料庫\n儲存所有門牌資料")]
    end

    subgraph 查詢層
        API["查詢 API\n提供門牌資料查詢服務"]
    end

    subgraph 使用者
        USR["使用者 / 考官\n透過網頁或 API 查詢"]
    end

    subgraph 通知
        LINE["異常通知\n發生錯誤時自動寄送 Email"]
    end

    SCH -->|"每天 08:00 自動觸發"| MAIN
    MAIN --> CFG
    MAIN --> DB1
    MAIN --> CSV
    CFG -->|"提供網址與查詢條件"| CRW
    MAIN -->|"依序查詢各行政區"| CRW
    CRW -->|"辨識驗證碼"| CAP
    CRW -->|"建立查詢連線（三步驟取得安全 token）"| WEB
    WEB -->|"回傳安全驗證 token"| CRW
    CRW -->|"送出查詢條件與驗證碼"| WEB
    WEB -->|"回傳查詢結果"| CRW
    CRW -->|"整理後的資料列表"| MAIN
    MAIN -->|"寫入 CSV 檔"| CSVF
    MAIN -->|"寫入資料庫"| PG
    USR -->|"送出查詢請求（城市 / 行政區）"| API
    API -->|"查詢資料庫"| PG
    PG -->|"回傳符合條件的資料"| API
    API -->|"回傳查詢結果"| USR
    MAIN -->|"爬蟲失敗時寄送通知"| LINE
    API -->|"查無資料時寄送通知"| LINE
```

---

## 圖 2：Log 監控流程

```mermaid
flowchart LR
    subgraph 應用服務
        CRW["爬蟲服務\n執行時輸出狀態紀錄"]
        API["查詢 API 服務\n每次查詢都輸出紀錄"]
    end

    subgraph Log 收集
        PT["Log 收集器\n自動抓取所有容器的執行紀錄"]
    end

    subgraph Log 儲存
        LK["Log 儲存引擎\n集中存放所有執行紀錄"]
    end

    subgraph 可視化
        GF["監控儀表板\n視覺化呈現紀錄\n可查詢任意時間範圍的歷史資料"]
    end

    subgraph 異常通知
        LINE["異常通知\n自動寄送 Email"]
    end

    subgraph 觀測者
        OPS["維運人員 / 考官\n查看監控畫面"]
    end

    CRW -->|"輸出執行紀錄"| PT
    API -->|"輸出執行紀錄"| PT
    PT -->|"推送 log 至儲存引擎"| LK
    LK -->|"查詢 log 資料"| GF
    GF -->|"顯示儀表板與歷史紀錄"| OPS
    CRW -->|"發生錯誤時觸發通知"| LINE
    API -->|"查無資料時觸發通知"| LINE
    LINE -->|"Gmail 寄信通知"| OPS
```

---

## 圖 3：Docker Compose 服務關係圖

```mermaid
flowchart TB
    subgraph docker-compose
        PG["資料庫\n其他服務啟動前需等待就緒"]
        CRW["爬蟲服務\n資料庫就緒後才啟動"]
        API["查詢 API\n資料庫就緒後才啟動"]
        LK["Log 儲存引擎\n接收並儲存所有紀錄"]
        PT["Log 收集器\nLog 儲存引擎就緒後才啟動"]
        GF["監控儀表板\nLog 儲存引擎就緒後才啟動"]
    end

    NET["內部網路\n所有容器透過此網路互相溝通"]

    PG --- NET
    CRW --- NET
    API --- NET
    LK --- NET
    PT --- NET
    GF --- NET

    CRW -->|"等資料庫就緒後才啟動"| PG
    API -->|"等資料庫就緒後才啟動"| PG
    PT -->|"推送 log"| LK
    GF -->|"查詢 log"| LK
```

---

## 元件選型說明

### 爬蟲：requests + BeautifulSoup

| 考量 | 說明 |
|------|------|
| **為何不用 Selenium** | 透過 Chrome DevTools → Network → XHR 分析，發現查詢結果是由後端 `/inquiry/date` API 回傳的 JSON，並非動態渲染的 HTML。直接呼叫 API 更快、更穩定，且不需安裝 Chrome / ChromeDriver |
| **為何不用 Scrapy** | Scrapy 適合大規模多站點爬取，本題為單一政府網站的 API 呼叫，requests 更輕量直覺 |
| **資安優勢** | requests 只發送明確定義的 HTTP 請求，不執行 JavaScript、不載入第三方資源，攻擊面遠小於 Selenium（無瀏覽器 CVE 風險、Docker 不需 `--no-sandbox`）。取得的資料為純 JSON，不含 HTML 標籤，寫入 PostgreSQL 再由 FastAPI 輸出時，整條資料鏈均為結構化資料，有效降低 XSS / Injection 風險 |
| **Session 管理** | `requests.Session` 自動維持 cookie，模擬完整瀏覽器 session，確保 CSRF token 與 captchaKey 在同一個 session 中有效 |
| **驗證碼策略** | ddddocr 自動辨識（前 8 次）→ 辨識失敗回空字串讓 server 換圖重試 → 最後 2 次切換人工輸入，確保一定能過 |
| **Docker 映像大小** | 不需 Chrome，映像從 ~500MB 縮小至 ~150MB |

### API：FastAPI

| 考量 | 說明 |
|------|------|
| **高效能** | 基於 ASGI（Starlette），非同步處理，適合 I/O 密集的 DB 查詢 |
| **自動文件** | 內建 Swagger UI（`/docs`），免寫額外 API 文件，考官可直接互動測試 |
| **型別驗證** | Pydantic 自動驗證 Request 格式，`city` 或 `township` 遺漏時回 422 |
| **模組化設計** | config / models / db / main 四個檔案各司其職，易於維護與說明 |

### 資料庫：PostgreSQL

| 考量 | 說明 |
|------|------|
| **關聯式結構** | 門牌資料欄位固定，關聯式 DB 查詢效率高且支援索引 |
| **容器化** | `postgres:15-alpine` 映像輕量，`healthcheck` 確保爬蟲 / API 在 DB 就緒後才啟動 |
| **環境切換** | 連線參數全部透過環境變數注入，從地端切換到雲端只需改 `.env` 的 `DB_HOST` |

### Log 監控：Grafana + Loki + Promtail

| 考量 | 說明 |
|------|------|
| **為何不用 ELK** | ELK（Elasticsearch + Logstash + Kibana）記憶體需求高（Elasticsearch 建議 8GB+），地端環境負擔重；Loki 僅索引 Label，儲存成本低 |
| **自動收集** | Promtail 掛載 Docker socket，自動發現所有容器，應用程式不需修改任何程式碼 |
| **開箱即用** | Grafana datasource 與儀表板全部自動 Provisioning，`docker-compose up` 後直接看到監控畫面 |
| **歷史查詢** | Grafana 右上角選時間範圍，可回查指定日期的爬蟲執行紀錄 |

### 異常通知：Email（Gmail SMTP）

| 考量 | 說明 |
|------|------|
| **通用性** | Email 為最通用的通知管道，不需安裝額外 App，收件人帳號即可 |
| **免費** | Gmail SMTP 免費，使用 App Password 驗證，無需額外套件（Python 內建 smtplib）|
| **容錯設計** | 環境變數未設定時程式不中斷，只印 WARNING log；通知失敗也不影響主流程 |

---

## 整體架構總覽

### 全地端模式（`make local`）

```
┌─────────────────────────────────────────────────────────────────┐
│                        Docker Compose                           │
│                                                                 │
│  ┌──────────────────┐    ┌───────────────┐    ┌─────────────┐  │
│  │     crawler      │    │      api      │    │  postgres   │  │
│  │  試題1           │    │  試題2        │    │  Port 5432  │  │
│  │  requests 直打API│    │  FastAPI      │    │             │  │
│  │  ddddocr OCR     │    │  Port 8000    │    └─────────────┘  │
│  │  APScheduler     │    │  Swagger UI   │          ▲          │
│  └────────┬─────────┘    └──────┬────────┘          │          │
│           │                     │           app-network        │
│           └─────────────────────┘──────────────────┘          │
│                                                                 │
│  ┌──────────────────┐    ┌───────────────┐    ┌─────────────┐  │
│  │      loki        │◄───│   promtail    │    │   grafana   │  │
│  │  試題3           │    │  試題3        │    │  試題3      │  │
│  │  Port 3100       │    │  Docker socket│    │  Port 3000  │  │
│  └──────────────────┘    └───────────────┘    └─────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                    │
                          Email 異常通知（Gmail SMTP）
```

---

## 圖 4：雲地並行架構（符合銀行法規）

```mermaid
flowchart TB
    subgraph GCP雲端["GCP 雲端（運算層）"]
        VM["雲端虛擬機\n每天 08:00 自動執行爬蟲\n不寫入資料庫，只輸出 CSV"]
        GCS["雲端儲存桶\n存放爬蟲產出的 CSV 檔"]
        CICD["自動部署流程\n推送程式碼後自動打包映像\n更新雲端爬蟲至最新版本"]
        SM["密碼保管庫\n集中管理敏感憑證\n（概念展示，未實作）"]
    end

    subgraph OnPrem["地端（資料中心）"]
        CRON["排程任務\n每天 09:00\n主動從雲端拉取 CSV"]
        PG[("資料庫\nPostgreSQL\n永遠在地端，不上雲")]
        API["查詢 API\nFastAPI Port 8000\n提供門牌查詢介面"]
        GF["監控儀表板\nGrafana Port 3000\n查看爬蟲與 API 紀錄"]
    end

    WEB["內政部戶政司\n門牌資料來源"]

    VM -->|"每天抓取 3187 筆資料"| WEB
    WEB -->|"回傳 JSON 查詢結果"| VM
    VM -->|"不寫入資料庫\n只輸出 CSV 存至雲端"| GCS
    GCS -->|"地端主動拉取\n雲端無法推送進內網"| CRON
    CRON -->|"匯入資料庫\n重複資料自動略過"| PG
    API -->|"查詢門牌資料"| PG
    CICD -->|"程式碼更新後\n自動部署新版本至雲端"| VM
```

---

## 雲地並行設計說明

### 為何符合銀行法規（金管會規範）

| 規範要點 | 本架構做法 |
|----------|-----------|
| **資料不出境** | PostgreSQL 僅在地端，雲端無 DB |
| **GCS Pull Model** | 地端主動拉取，雲端無法推送進行內網 |
| **運算彈性** | 爬蟲在雲端彈性擴展，不佔用地端資源 |
| **稽核追蹤** | GCS 保留 CSV 原始記錄，地端 DB 保留入庫紀錄 |
| **金鑰管理** | Secret Manager 集中管理敏感憑證（不寫在程式碼） |

### 兩種模式對照

| 項目 | 全地端模式 | 雲地並行模式 |
|------|-----------|------------|
| 啟動指令 | `make local` | `make cloud` + GCP VM scheduler |
| 爬蟲位置 | 本機 Docker | GCP VM Docker |
| DB 位置 | 本機 PostgreSQL | **本機 PostgreSQL（不變）** |
| API 位置 | 本機 Port 8000 | 本機 Port 8001 |
| Grafana | Port 3000 | Port 3001 |
| 資料同步 | 直接寫入 | GCS → `make pull` → 本機 DB |
