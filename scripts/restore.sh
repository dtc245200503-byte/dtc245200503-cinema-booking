#!/usr/bin/env bash
# Khôi phục CSDL từ file .sql:  bash scripts/restore.sh backups/cinema_xxx.sql
set -euo pipefail
cd "$(dirname "$0")/.."
FILE="${1:?Cần truyền đường dẫn file .sql}"
[ -f "$FILE" ] || { echo "Không thấy file: $FILE"; exit 1; }
read -r -p "Thao tác sẽ GHI ĐÈ dữ liệu hiện tại. Gõ 'yes' để tiếp tục: " ok
[ "$ok" = "yes" ] || { echo "Đã hủy."; exit 1; }
docker compose stop backend
docker compose exec -T db sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' < "$FILE"
docker compose start backend
echo "Đã khôi phục từ $FILE"
