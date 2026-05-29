@echo off
echo 啟動所有服務...
docker compose down
copy .env.local .env
docker compose up -d
echo 等待服務啟動...
timeout /t 5 /nobreak >nul
start http://localhost:8000/docs
start http://localhost:3000
echo.
echo 啟動完成
echo   API Swagger ^> http://localhost:8000/docs
echo   Grafana     ^> http://localhost:3000 (admin/admin)
