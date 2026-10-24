FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
COPY entrypoint.sh .
# Không chạy bằng root: tạo người dùng không đặc quyền
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin appuser \
 && chmod 755 entrypoint.sh \
 && mkdir -p /data/uploads/posters && chown -R 10001:10001 /data/uploads
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"
ENTRYPOINT ["./entrypoint.sh"]
