#!/bin/sh
# Khởi động container backend: dọn thư mục số liệu, nạp dữ liệu mẫu, chạy Gunicorn.
set -e
mkdir -p /tmp/prom && rm -rf /tmp/prom/*
python -m app.seed
exec gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000 \
     --worker-tmp-dir /tmp --access-logfile - --error-logfile - app.main:app
