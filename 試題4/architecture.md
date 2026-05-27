# 試題 4 - 系統架構圖

---

## 圖 1：資料流程圖

```mermaid
flowchart TD
    subgraph 排程層
        SCH["⏰ APScheduler\nscheduler.py\n每天 08:00 觸發"]
    end

    subgraph 爬蟲層
        CFG["⚙️ config.py\nURL / 查詢條件"]
        CAP["🔍 captcha.py\nddddocr OCR 辨識"]
        CRW["🕷️ crawler.py\nDoorplateCrawler\n純 requests，直打 API"]
        DB1["🗄️ db.py\nPostgreSQL 操作"]
        CSV["📄 csv_exporter.py\nresult.csv 落檔"]
        MAIN["▶️ main.py\n進入點 / Logger"]
    end

    subgraph 外部資源
        WEB["🌐 內政部戶政司\nris.gov.tw\n/inquiry/date API\n回傳 jqGrid JSON"]
    end

    subgraph 儲存層
        CSVF["📄 output/result.csv"]
        PG[("🗄️ PostgreSQL\ndoor_plate_data\nDocker container")]
    end

    subgraph 查詢層
        API["⚡ FastAPI\nmain.py\nPort 8000"]
    end

    subgraph 使用者
        USR["👤 使用者 / 考官\ncurl / Swagger UI"]
    end

    subgraph 通知
        LINE["📱 LINE Notify\nnotify.py"]
    end

    SCH -->|"每天 08:00 呼叫 main()"| MAIN
    MAIN --> CFG
    MAIN --> DB1
    MAIN --> CSV
    CFG -->|"URL / 參數"| CRW
    MAIN -->|"query_district()"| CRW
    CRW -->|"solve_auto()"| CAP
    CRW -->|"3 步驟建立 session\nGET main → POST map → POST query"| WEB
    WEB -->|"captchaKey + CSRF"| CRW
    CRW -->|"POST /inquiry/date\n帶 captchaInput + captchaKey"| WEB
    WEB -->|"jqGrid JSON\n{rows:[{cell:[地址,日期,類別]}]}"| CRW
    CRW -->|"Record 列表"| MAIN
    MAIN -->|"write_csv()"| CSVF
    MAIN -->|"save_records()"| PG
    USR -->|"POST /query\n{city, township}"| API
    API -->|"SELECT WHERE\ncity AND township"| PG
    PG -->|"查詢結果"| API
    API -->|"JSON Response\n{count, data}"| USR
    MAIN -->|"爬蟲失敗 / 警告"| LINE
    API -->|"查詢結果為空"| LINE
```

---

## 圖 2：Log 監控流程

```mermaid
flowchart LR
    subgraph 應用服務
        CRW["🕷️ Crawler\nstdout log\n格式：時間｜等級｜訊息"]
        API["⚡ FastAPI API\nstdout log\n格式：時間｜等級｜訊息"]
    end

    subgraph Log 收集
        PT["📡 Promtail\npromtail-config.yml\n掛載 Docker socket\n自動收集所有容器 log"]
    end

    subgraph Log 儲存
        LK["🗃️ Loki\nloki-config.yml\n儲存於 /loki/chunks\nPort 3100"]
    end

    subgraph 可視化
        GF["📊 Grafana\nPort 3000\n自動載入儀表板\n爬蟲 / API / 異常 3 個面板\n歷史紀錄可指定時間範圍"]
    end

    subgraph 異常通知
        LINE["📱 LINE Notify\n即時推播\n爬蟲異常 / 查詢為空"]
    end

    subgraph 觀測者
        OPS["👤 維運人員 / 考官\nhttp://localhost:3000"]
    end

    CRW -->|"stdout"| PT
    API -->|"stdout"| PT
    PT -->|"HTTP Push\n/loki/api/v1/push"| LK
    LK -->|"LogQL 查詢"| GF
    GF -->|"儀表板 / 歷史搜尋"| OPS
    CRW -->|"ERROR / CRITICAL"| LINE
    API -->|"WARNING（查無資料）"| LINE
    LINE -->|"LINE App 推播"| OPS
```

---

## 圖 3：Docker Compose 服務關係圖

```mermaid
flowchart TB
    subgraph docker-compose
        PG["🗄️ postgres\nPort 5432\nhealthcheck 確認就緒"]
        CRW["🕷️ crawler\n試題1\ndepends_on: postgres"]
        API["⚡ api\n試題2\nPort 8000\ndepends_on: postgres"]
        LK["🗃️ loki\n試題3\nPort 3100"]
        PT["📡 promtail\n試題3\ndepends_on: loki"]
        GF["📊 grafana\n試題3\nPort 3000\ndepends_on: loki"]
    end

    NET["🔗 app-network\nbridge（容器間以 service 名稱互通）"]

    PG --- NET
    CRW --- NET
    API --- NET
    LK --- NET
    PT --- NET
    GF --- NET

    CRW -->|"等 DB 就緒"| PG
    API -->|"等 DB 就緒"| PG
    PT -->|"push log"| LK
    GF -->|"LogQL 查詢"| LK
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

### 異常通知：LINE Notify

| 考量 | 說明 |
|------|------|
| **台灣普及率** | LINE 在台灣使用率極高，維運人員幾乎都有帳號，不需額外安裝 App |
| **免費無限量** | 個人 Token 無訊息數量限制 |
| **容錯設計** | Token 留空時程式不中斷，只印 WARNING log；通知失敗也不影響主流程 |

---

## 整體架構總覽

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
                          LINE Notify（對外通知）
```
