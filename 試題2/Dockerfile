# ============================================================
# 試題 2 - FastAPI 查詢 API 容器
# Base：python:3.11-slim（輕量，不需要 Chrome）
# ============================================================

FROM python:3.11-slim

# Python output 不緩衝，確保 log 即時被 Promtail 收集
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# ── 安裝 Python 套件 ──────────────────────────────────────────
# 先複製 requirements.txt，利用 Docker layer cache
# 只有套件有異動時才重新安裝，加快重建速度
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── 複製程式碼 ────────────────────────────────────────────────
COPY . .

# ── 開放 API Port ─────────────────────────────────────────────
EXPOSE 8000

# ── 啟動 FastAPI（--host 0.0.0.0 讓容器外部可連線）─────────
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
