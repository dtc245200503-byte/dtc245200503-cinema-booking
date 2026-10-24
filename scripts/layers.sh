#!/usr/bin/env bash
# Cập nhật COMPOSE_FILE trong .env theo các lớp docker-compose.*.yml hiện có.
# Chạy lại sau khi thêm lớp mới (giám sát, log, hardening) để `docker compose up -d` nạp thêm lớp đó.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] || { echo "Chưa có .env, hãy chạy: bash scripts/init.sh <IP>"; exit 1; }
FILES="docker-compose.yml"
for layer in monitoring logging hardening; do        # thứ tự quan trọng: hardening nạp cuối
  [ -f "docker-compose.$layer.yml" ] && FILES="$FILES:docker-compose.$layer.yml"
done
if grep -q '^COMPOSE_FILE=' .env; then
  sed -i "s|^COMPOSE_FILE=.*|COMPOSE_FILE=$FILES|" .env
else
  echo "COMPOSE_FILE=$FILES" >> .env
fi
echo "COMPOSE_FILE=$FILES"
