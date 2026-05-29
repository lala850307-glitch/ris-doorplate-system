# ============================================================
# 使用說明：
#   make local        啟動全地端模式
#   make cloud        啟動雲地混合模式（可與地端同時跑）
#   make crawl-local  執行爬蟲（寫入地端 DB）
#   make crawl-cloud  執行爬蟲（寫入 GCP DB）
#   make stop         停止全部
# ============================================================

local:		## 全地端模式（DB + API + 監控全跑本機）
	docker compose down
	cp .env.local .env
	docker compose up -d
	@echo "⏳ 等待服務啟動..."
	@sleep 5
	open http://localhost:8000
	open http://localhost:3000
	@echo "✅ 地端模式啟動完成"
	@echo "   API     → http://localhost:8000"
	@echo "   Grafana → http://localhost:3000"

cloud:		## 雲地混合模式（DB 在 GCP，可與地端同時跑）
	docker compose -f docker-compose.cloud.yml down
	docker compose -f docker-compose.cloud.yml up -d
	@echo "⏳ 等待服務啟動..."
	@sleep 5
	open http://localhost:8001
	open http://localhost:3001
	@echo "✅ 雲地模式啟動完成"
	@echo "   API     → http://localhost:8001（連 GCP DB）"
	@echo "   Grafana → http://localhost:3001"

crawl-local: ## 執行爬蟲（寫入地端 DB）
	cp .env.local .env
	docker compose up crawler

crawl-cloud: ## 執行爬蟲（寫入 GCP DB，走 SSL）
	cp .env.cloud .env
	docker compose up crawler

stop-local:	## 停止地端服務
	docker compose down

stop-cloud:	## 停止雲地服務
	docker compose -f docker-compose.cloud.yml down

stop:		## 停止全部服務
	docker compose down
	docker compose -f docker-compose.cloud.yml down

logs:		## 查看爬蟲即時 log
	docker compose logs -f crawler
