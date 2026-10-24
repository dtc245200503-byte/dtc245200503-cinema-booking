#!/usr/bin/env bash
# Chuẩn bị chạy lần đầu: sinh .env (mật khẩu ngẫu nhiên mạnh), chứng chỉ HTTPS tự ký, file bí mật cho exporter.
# Dùng:  bash scripts/init.sh <IP hoặc tên máy chủ>        ví dụ: bash scripts/init.sh 192.168.198.134
# Nếu cổng 80/443 đã bị dùng:  HTTP_PORT=8088 HTTPS_PORT=8443 bash scripts/init.sh <IP>
set -euo pipefail
cd "$(dirname "$0")/.."

HOST="${1:-localhost}"
HTTP_PORT="${HTTP_PORT:-80}"
HTTPS_PORT="${HTTPS_PORT:-443}"
rand() { openssl rand -hex "$1"; }

if [ -f .env ]; then
  echo ".env đã tồn tại nên giữ nguyên (xóa file này nếu muốn sinh lại mật khẩu)."
else
  PUBLIC_URL="https://$HOST"
  [ "$HTTPS_PORT" != "443" ] && PUBLIC_URL="$PUBLIC_URL:$HTTPS_PORT"
  cat > .env <<ENV
# Sinh tự động bởi scripts/init.sh. KHÔNG commit file này lên GitHub.
PUBLIC_URL=$PUBLIC_URL
HTTP_PORT=$HTTP_PORT
HTTPS_PORT=$HTTPS_PORT
MYSQL_DATABASE=cinema
MYSQL_ROOT_PASSWORD=$(rand 16)
APP_DB_PASSWORD=$(rand 16)
EXPORTER_DB_PASSWORD=$(rand 16)
SECRET_KEY=$(rand 32)
GRAFANA_ADMIN_PASSWORD=$(rand 8)Gr1-
ADMIN_PASSWORD=$(rand 6)Aa1-
DEMO_PASSWORD=$(rand 6)Kh1-
ENV
  chmod 600 .env
  echo "Đã tạo .env với mật khẩu ngẫu nhiên."
fi

bash scripts/layers.sh
set -a; . ./.env; set +a
mkdir -p certs secrets backups

if [ ! -f certs/server.crt ]; then
  if [[ "$HOST" =~ ^[0-9.]+$ ]]; then SAN="IP:$HOST,DNS:localhost"; else SAN="DNS:$HOST,DNS:localhost"; fi
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout certs/server.key -out certs/server.crt -subj "/CN=$HOST" -addext "subjectAltName=$SAN"
  chmod 644 certs/server.crt certs/server.key      # Nginx (uid 101) trong container cần đọc
  echo "Đã tạo chứng chỉ HTTPS tự ký cho $HOST."
fi

cat > secrets/mysqld-exporter.cnf <<CNF
[client]
user=exporter
password=${EXPORTER_DB_PASSWORD}
host=db
port=3306
CNF
chmod 644 secrets/mysqld-exporter.cnf

cat <<MSG

=== Sẵn sàng. Chạy:  docker compose up -d --build ===
Địa chỉ        : ${PUBLIC_URL}
Quản trị web   : admin@cinema.local   / ${ADMIN_PASSWORD}
Khách mẫu      : khach@cinema.local   / ${DEMO_PASSWORD}
Grafana        : ${PUBLIC_URL}/grafana/   admin / ${GRAFANA_ADMIN_PASSWORD}
phpMyAdmin     : ${PUBLIC_URL}/pma/       cinema_app / ${APP_DB_PASSWORD}
(Tất cả mật khẩu được lưu trong file .env)
MSG
