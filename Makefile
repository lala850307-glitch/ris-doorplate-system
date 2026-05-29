# ============================================================
# 使用說明：
#   make local       啟動全地端模式（DB + API + 監控）
#   make crawl       執行爬蟲（寫入地端 DB）
#   make pull        從 GCS 下載 CSV，匯入地端 PostgreSQL
#   make stop        停止所有服務
#   make logs        查看爬蟲即時 log
# ============================================================

local:		## 全地端模式（DB + API + 監控全跑本機）
	docker compose down
	cp .env.local .env
	docker compose up -d
	@echo "⏳ 等待服務啟動..."
	@sleep 5
	open http://localhost:8000/docs
	open http://localhost:3000
	@echo "✅ 啟動完成"
	@echo "   API Swagger → http://localhost:8000/docs"
	@echo "   API 靜態頁  → http://localhost:8000"
	@echo "   Grafana     → http://localhost:3000 (admin/admin)"

crawl:		## 執行爬蟲（寫入地端 DB）
	docker rm -f crawler 2>/dev/null; true
	cp .env.local .env
	docker compose up crawler

pull:		## 雲地模式：從 GCS 下載 CSV，匯入地端 PostgreSQL
	bash pull_from_gcs.sh

stop:		## 停止所有服務
	docker compose down

logs:		## 查看爬蟲即時 log
	docker compose logs -f crawler
