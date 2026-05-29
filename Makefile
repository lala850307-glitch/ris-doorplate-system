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
	@API_PORT=$$(for p in $$(seq 8000 8100); do nc -z localhost $$p 2>/dev/null || { echo $$p; break; }; done); \
	 GF_PORT=$$(for p in $$(seq 3000 3100); do nc -z localhost $$p 2>/dev/null || { echo $$p; break; }; done); \
	 echo "使用 Port：API=$$API_PORT  Grafana=$$GF_PORT"; \
	 API_PORT=$$API_PORT GF_PORT=$$GF_PORT docker compose up -d && \
	 sleep 5 && \
	 open http://localhost:$$API_PORT && \
	 open http://localhost:$$API_PORT/docs && \
	 open http://localhost:$$GF_PORT && \
	 echo "✅ 啟動完成" && \
	 echo "   API 靜態頁  → http://localhost:$$API_PORT" && \
	 echo "   API Swagger → http://localhost:$$API_PORT/docs" && \
	 echo "   Grafana     → http://localhost:$$GF_PORT (admin/admin)"

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
