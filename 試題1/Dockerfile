# ============================================================
# 試題 1 - 爬蟲容器（requests 版）
# Base：python:3.11-slim
#
# 改用 requests 直打 API 後，不需要 Chrome / ChromeDriver /
# Tesseract，映像大幅縮小（約 500MB → 150MB）。
#
# 本機執行：
#   pip install -r requirements.txt
#   python main.py          ← 單次執行
#   python scheduler.py     ← 排程模式
#
# Docker 執行：
#   docker-compose up crawler
# ============================================================

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN mkdir -p output/captcha logs

# 先複製 requirements，利用 Docker layer cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 預設跑排程版；單次執行改成：docker-compose run crawler python main.py
CMD ["python", "scheduler.py"]
