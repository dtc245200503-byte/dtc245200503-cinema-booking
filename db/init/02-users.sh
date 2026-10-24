#!/bin/bash
# Tạo tài khoản DB với quyền tối thiểu (nguyên tắc đặc quyền tối thiểu).
#  - cinema_app: chỉ SELECT/INSERT/UPDATE/DELETE trên CSDL ứng dụng, KHÔNG có DROP/ALTER/CREATE.
#  - exporter  : chỉ đủ quyền để mysqld-exporter đọc số liệu giám sát.
# Biến môi trường được truyền từ docker-compose.
mysql -uroot -p"${MYSQL_ROOT_PASSWORD}" <<SQL
CREATE USER 'cinema_app'@'%' IDENTIFIED BY '${APP_DB_PASSWORD}';
GRANT SELECT, INSERT, UPDATE, DELETE ON \`${MYSQL_DATABASE}\`.* TO 'cinema_app'@'%';
CREATE USER 'exporter'@'%' IDENTIFIED BY '${EXPORTER_DB_PASSWORD}' WITH MAX_USER_CONNECTIONS 3;
GRANT PROCESS, REPLICATION CLIENT, SELECT ON *.* TO 'exporter'@'%';
FLUSH PRIVILEGES;
SQL
