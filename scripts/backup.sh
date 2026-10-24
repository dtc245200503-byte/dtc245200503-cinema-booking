#!/usr/bin/env bash
# Sao lưu cơ sở dữ liệu MySQL và thư mục ảnh poster vào ./backups (giữ 7 ngày).
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p backups
TS="$(date +%Y%m%d_%H%M%S)"
docker compose exec -T db sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines "$MYSQL_DATABASE"' \
  > "backups/cinema_${TS}.sql"
docker run --rm -v cinema_uploads:/data:ro -v "$PWD/backups":/backup alpine \
  tar czf "/backup/uploads_${TS}.tgz" -C /data . 2>/dev/null || echo "(chưa có ảnh poster để sao lưu)"
find backups \( -name 'cinema_*.sql' -o -name 'uploads_*.tgz' \) -mtime +7 -delete
echo "Đã sao lưu: backups/cinema_${TS}.sql ($(du -h "backups/cinema_${TS}.sql" | cut -f1))"
