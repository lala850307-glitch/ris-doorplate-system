local:		## 全地端模式（DB + API + 監控全跑本機）
	cp .env.local .env
	docker compose up -d
	@echo "⏳ 等待服務啟動..."
	@sleep 5
	open http://localhost:8000
	open http://localhost:3000

cloud:		## 雲地混合模式（DB 在 GCP，其他本機）
	cp .env.cloud .env
	docker compose up -d api loki promtail grafana
	@echo "⏳ 等待服務啟動..."
	@sleep 5
	open http://localhost:8000
	open http://localhost:3000

crawl:		## 執行爬蟲（依目前 .env 決定連地端或雲端 DB）
	docker compose up crawler

stop:		## 停止所有服務
	docker compose down

logs:		## 查看爬蟲即時 log
	docker compose logs -f crawler
