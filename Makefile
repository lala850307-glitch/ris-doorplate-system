start:
	docker compose up -d
	@echo "⏳ 等待服務啟動..."
	@sleep 5
	open http://localhost:8000
	open http://localhost:3000

stop:
	docker compose down

restart:
	docker compose down
	docker compose up -d

logs:
	docker compose logs -f crawler
