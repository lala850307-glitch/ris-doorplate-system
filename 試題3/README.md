# 試題 3 - Log 收集與異常通報

## 說明

使用 **Grafana + Loki + Promtail** 收集爬蟲與 API 的 log，提供即時監控與歷史查詢。
異常情況由試題 1 / 試題 2 的 `notify.py` 透過 Email 通報。

---

## 架構

```
crawler / api（stdout log）
        │
        ▼
Promtail（掛載 Docker socket，自動收集所有容器 log）
        │  HTTP Push
        ▼
Loki（儲存 log，Port 3100）
        │  LogQL 查詢
        ▼
Grafana（監控儀表板，Port 3000）
```

---

## 啟動方式

從根目錄執行，監控服務會與其他服務一起啟動：

```bash
make local
```

---

## 進入 Grafana

1. 開啟瀏覽器：http://localhost:3000
2. 帳號：`admin`
3. 密碼：`admin`
4. 首頁會自動顯示「🏨 門牌爬蟲監控儀表板」

---

## 儀表板說明

儀表板包含以下面板（自動 Provisioning，無需手動匯入）：

| 面板 | 說明 | 正常值 |
|------|------|--------|
| 🚨 ERROR 次數 | 爬蟲或 API 發生錯誤的次數 | 0 |
| ⚠️ WARNING 次數 | 驗證碼重試、查詢為空等警告 | 幾十次（正常） |
| ✅ 爬蟲成功區數 | 成功完成的行政區數量 | 12（全部成功） |
| 📡 API 查詢次數 | `/query` 被呼叫的次數 | 依實際使用 |
| 📈 Log 量折線圖 | 每分鐘 log 行數（crawler / api） | 爬蟲跑時有尖峰 |
| 🕷 爬蟲 Log | crawler 容器即時 log | — |
| 🚀 API Log | api 容器即時 log | — |
| 🚨 ERROR/WARNING Log | 異常 log 彙整 | — |

> **時間範圍建議**：使用 `Last 30 minutes` 或 `Last 1 hour` 查看完整爬蟲執行結果。

---

## 常用 LogQL 查詢語法

在 Grafana → Explore → Loki 輸入：

```logql
# 爬蟲所有 log
{container_name="crawler"}

# API 所有 log
{container_name="api"}

# 只看 ERROR
{container_name=~"api|crawler"} |= "ERROR"

# 只看 WARNING
{container_name=~"api|crawler"} |= "WARNING"

# 查詢特定行政區的爬取紀錄
{container_name="crawler"} |= "大安區"

# 查看 Email 通知發送紀錄
{container_name=~"api|crawler"} |= "Email 通知"
```

---

## 歷史紀錄查詢

在 Grafana 右上角選擇時間範圍：

- **Last 30 minutes**：查看最近一次爬蟲執行
- **Last 24 hours**：查看今日所有執行紀錄
- **Custom range**：自訂起訖時間

---

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `loki-config.yml` | Loki 設定，log chunks 儲存於 `/loki` |
| `promtail-config.yml` | Promtail 設定，透過 Docker socket 自動收集容器 log |
| `promtail-positions/positions.yaml` | Promtail 讀取位置，重啟後不重複收集（自動維護） |
| `grafana/provisioning/datasources/loki.yml` | 自動設定 Loki 為 Grafana 資料來源 |
| `grafana/provisioning/dashboards/dashboard.yml` | 自動載入儀表板的設定 |
| `grafana/provisioning/dashboards/json/crawler-monitor.json` | 爬蟲監控儀表板定義 |

---

## 注意事項

**每次完整清理時，須同時清除 Loki 資料和 positions 檔案：**

```bash
# 正確的完整清理方式（兩個必須一起做）
docker rm -f crawler api
docker compose stop loki promtail
docker volume rm ris-doorplate-system_loki_data
rm -f 試題3/promtail-positions/positions.yaml
docker compose up -d
```

> ⚠️ 只清 positions 不清 Loki（或反之），會導致 log 重複注入，造成儀表板數字異常。
