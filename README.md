# Hệ thống Đặt vé Xem phim / Sự kiện: triển khai bằng Docker Compose

Môn: Triển khai và Quản trị Hệ thống Phần mềm. Đề 11: Hệ thống Đặt vé Xem phim / Sự kiện (MySQL + phpMyAdmin).

Sinh viên: Nguyễn Văn Thanh, MSSV DTC245200503, lớp CNTT K23M.

Toàn bộ hệ thống chạy bằng **Docker Compose**: ứng dụng web, cơ sở dữ liệu, công cụ quản lý DB, reverse proxy, giám sát, log tập trung và các biện pháp hardening.

## 1. Kiến trúc

```
Trình duyệt ──HTTPS──> Nginx (cổng 80/443, duy nhất mở ra ngoài)
                        ├── /          giao diện React (file tĩnh)
                        ├── /api/      backend FastAPI (Gunicorn + Uvicorn) ──> MySQL 8
                        ├── /uploads/  ảnh poster (volume chỉ đọc)
                        ├── /pma/      phpMyAdmin ──> MySQL
                        └── /grafana/  Grafana
Giám sát : Prometheus <── backend (/metrics), cAdvisor (container), mysqld-exporter (MySQL), nginx-exporter (Nginx)
Log      : Promtail (đọc log mọi container qua docker.sock) ──> Loki ──> Grafana (LogQL)
```

| Dịch vụ | Image | Vai trò |
|---|---|---|
| nginx | nginx-unprivileged 1.27 (build cùng React) | Reverse proxy, HTTPS tự ký, security headers, giới hạn đăng nhập |
| backend | python:3.12-slim (build) | API FastAPI: đặt vé, thanh toán giả lập, hoàn tiền, tải ảnh poster |
| db | mysql:8.0 | Cơ sở dữ liệu |
| phpmyadmin | phpmyadmin:5.2-apache | Công cụ quản lý MySQL |
| prometheus, grafana | prom/prometheus 2.53, grafana 11.2 | Thu thập số liệu và biểu đồ |
| cadvisor, mysqld-exporter, nginx-exporter | cadvisor 0.49, mysqld-exporter 0.15, nginx-exporter 1.3 | Số liệu container, MySQL, Nginx |
| loki, promtail | grafana/loki, promtail 2.9.8 | Log tập trung |

Cách ly mạng: `edge` (chỉ Nginx), `app`, `data`, `monitoring` (ba mạng sau là *internal*, container không ra được Internet). MySQL không publish cổng nào.

## 2. Cấu trúc thư mục

```
backend/      FastAPI (app/, tests/, Dockerfile)
frontend/     React + TypeScript (Vite), Dockerfile build rồi chạy bằng Nginx
db/init/      01-schema.sql (lược đồ), 02-users.sh (tài khoản DB quyền tối thiểu)
nginx/        default.conf, security-headers.conf
phpmyadmin/   config.user.inc.php (khóa đăng nhập root)
monitoring/   prometheus, grafana (provisioning + dashboard), loki, promtail
scripts/      init.sh, layers.sh, backup.sh, restore.sh
docker-compose.yml              lớp 1: MySQL, phpMyAdmin, backend, Nginx
docker-compose.monitoring.yml   lớp 2: Prometheus, Grafana, cAdvisor, exporter
docker-compose.logging.yml      lớp 3: Loki, Promtail
docker-compose.hardening.yml    lớp 4: hardening container
```

Các lớp được nạp cùng lúc qua biến `COMPOSE_FILE` trong `.env`, nên chỉ cần một lệnh `docker compose up -d`.

## 3. Yêu cầu

Ubuntu Server 24.04 (hoặc máy có Docker), Docker Engine và Docker Compose v2, RAM từ 4 GB, ổ đĩa trống từ 10 GB, có Internet để tải image.

Cài Docker nếu chưa có: `sudo apt-get install -y docker.io docker-compose-v2`, sau đó `sudo usermod -aG docker $USER` và đăng nhập lại.

## 4. Chạy hệ thống

```bash
git clone <địa chỉ repo> cinema && cd cinema
bash scripts/init.sh 192.168.198.134      # thay bằng IP hoặc tên máy chủ của em
docker compose up -d --build
docker compose ps                          # các dịch vụ phải ở trạng thái running / healthy
```

`init.sh` sinh `.env` với mật khẩu ngẫu nhiên, chứng chỉ HTTPS tự ký, file bí mật cho exporter và in ra tài khoản đăng nhập. Nếu cổng 80/443 đã bị dịch vụ khác dùng: `HTTP_PORT=8088 HTTPS_PORT=8443 bash scripts/init.sh <IP>`, rồi dùng địa chỉ https trực tiếp (không đi qua cổng HTTP).

| Địa chỉ | Dùng để |
|---|---|
| `https://<IP>/` | Website đặt vé (trình duyệt cảnh báo chứng chỉ tự ký: chọn Nâng cao, Tiếp tục) |
| `https://<IP>/pma/` | phpMyAdmin, đăng nhập `cinema_app` (mật khẩu `APP_DB_PASSWORD` trong `.env`) |
| `https://<IP>/grafana/` | Grafana, tài khoản `admin` (mật khẩu `GRAFANA_ADMIN_PASSWORD`) |
| `http://127.0.0.1:9095` | Giao diện Prometheus (chỉ trên máy chủ; từ máy khác dùng `ssh -L 9095:127.0.0.1:9095`) |

Dừng, xóa dữ liệu: `docker compose down` (giữ dữ liệu), `docker compose down -v` (xóa cả dữ liệu, kể cả lược đồ DB để nạp lại từ đầu).

## 5. Chức năng ứng dụng

Khách hàng: đăng ký, đăng nhập, xem phim và sự kiện, chọn ghế, giữ ghế 10 phút, thanh toán giả lập (có tùy chọn giả lập thất bại), hủy vé (hoàn 100% nếu còn từ 24 giờ, 50% nếu còn từ 2 giờ, dưới 2 giờ không cho hủy), xem lịch sử.

Quản trị viên: thêm phim và sự kiện **kèm ảnh poster** (JPG, PNG, WEBP, tối đa 2 MB, có xem trước), đổi hoặc xóa ảnh poster, quản lý phòng và suất chiếu, duyệt hoặc từ chối hoàn tiền, hủy suất chiếu (hoàn tiền hàng loạt), thống kê doanh thu, nhật ký thao tác.

Chống đặt trùng ghế: khóa dòng suất chiếu (`SELECT ... FOR UPDATE`) cộng ràng buộc `UNIQUE (showtime_id, seat_id, active)`. MySQL không có partial index nên cột `active` bằng 1 khi ghế đang giữ hoặc đã bán, `NULL` khi đã nhả.

## 6. Kết quả theo từng yêu cầu của đề

### Bước 1-2: Ứng dụng, MySQL, phpMyAdmin
Mở `https://<IP>/`, đăng ký và đặt vé. Mở `/pma/`, đăng nhập `cinema_app`, xem các bảng `movies`, `bookings`, `payments`.

### Bước 3: Nginx reverse proxy (commit 1)
HTTPS tự ký (TLS 1.2/1.3), chuyển HTTP sang HTTPS, `server_tokens off`, các header `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy` cho giao diện, giới hạn 5 lần đăng nhập mỗi phút.
```bash
curl -skI https://localhost/ | grep -iE "x-frame|x-content|content-security|server:"
```

### Bước 4: Prometheus và Grafana (commit 2)
Prometheus thu thập từ 5 nguồn (chính nó, API, cAdvisor, MySQL, Nginx). Grafana có bảng *Cinema - Giám sát hệ thống* gồm trạng thái dịch vụ, request/giây, độ trễ p95, CPU và RAM từng container, kết nối và truy vấn MySQL, kết nối Nginx.

Kiểm tra: Prometheus (`http://127.0.0.1:9095/targets`) phải có cả 5 mục ở trạng thái UP. Tạo tải để thấy biểu đồ nhảy: `for i in $(seq 1 300); do curl -sk https://localhost/api/movies >/dev/null; done`.

### Bước 5: Loki và Promtail, LogQL (commit 3)
Sau khi thêm lớp log: `docker compose up -d && docker compose restart grafana` (để Grafana nạp thêm nguồn dữ liệu Loki). Trong Grafana vào Explore, chọn nguồn Loki và thử các truy vấn:

```logql
{service="backend"}                                                     # toàn bộ log của backend
{service="nginx"} |= "POST /api/auth/login"                             # các lần gọi đăng nhập
{service="backend"} |~ "(?i)error|exception|traceback"                  # log lỗi
sum by (service) (rate({job="docker"}[1m]))                             # tốc độ sinh log theo dịch vụ
sum(count_over_time({service="nginx"} |= "POST /api/auth/login" |= "429" [5m]))   # lần đăng nhập bị chặn
```

Tạo dữ liệu cho truy vấn thứ 5: gửi liên tiếp nhiều lần đăng nhập sai sẽ bị Nginx trả 429.
```bash
for i in $(seq 1 12); do curl -sk -o /dev/null -w "%{http_code}\n" -X POST https://localhost/api/auth/login \
  -H 'Content-Type: application/json' -d '{"email":"x@x.vn","password":"sai"}'; done
```
Bảng điều khiển *Cinema - Log tập trung (Loki)* hiển thị sẵn các truy vấn trên.

### Bước 6: Hardening
| Biện pháp | Cách làm | Kiểm tra |
|---|---|---|
| Container không chạy root | backend (uid 10001), Nginx unprivileged (uid 101), MySQL (999), Grafana (472), Prometheus, Loki | `docker compose exec backend id`, `docker compose exec nginx id` |
| Cách ly mạng | 3 mạng internal; chỉ Nginx publish 80/443; DB không publish; container nội bộ không ra Internet | `docker ps --format 'table {{.Names}}\t{{.Ports}}'`; `docker compose exec backend python -c "import urllib.request as u; u.urlopen('http://1.1.1.1', timeout=3)"` phải lỗi |
| Mật khẩu mạnh | Mật khẩu ngẫu nhiên do `init.sh` sinh, lưu `.env` (quyền 600, không đưa lên Git); không có mật khẩu mặc định | `ls -l .env` |
| Hạn chế quyền DB | Ứng dụng dùng `cinema_app` chỉ có SELECT/INSERT/UPDATE/DELETE; `exporter` chỉ đủ quyền giám sát; phpMyAdmin khóa đăng nhập root | `docker compose exec db sh -c 'mysql -ucinema_app -p"$APP_DB_PASSWORD" cinema -e "DROP TABLE users"'` phải báo *DROP command denied* |
| Security headers và giới hạn đăng nhập | Cấu hình trong Nginx | xem Bước 3 và Bước 5 |
| Giới hạn container | `read_only`, `cap_drop: ALL`, `no-new-privileges`, giới hạn RAM và số tiến trình | `docker inspect cinema-backend --format '{{.HostConfig.ReadonlyRootfs}} {{.HostConfig.CapDrop}}'` |
| Kiểm tra tải ảnh | Chỉ nhận JPG/PNG/WEBP theo nội dung file, tối đa 2 MB, đặt tên ngẫu nhiên, thư mục ảnh Nginx chỉ đọc, CSP `default-src 'none'` | tải thử file `.html` đổi tên `.png` phải bị từ chối |

Ngoại lệ có chủ ý: phpMyAdmin (Apache khởi động bằng root rồi hạ quyền), cAdvisor (cần đọc cgroup của máy chủ), Promtail (cần đọc `docker.sock` ở chế độ chỉ đọc).

## 7. Quy trình commit trên GitHub

Tài khoản và repository đặt tên theo MSSV, ví dụ `dtc245200503/cinema-booking`. Chạy toàn bộ hệ thống một lần (mục 4) và kiểm tra từng bước 1-6 xong, sau đó chia commit theo từng nhóm file để lịch sử thể hiện đúng từng giai đoạn:

```bash
git init && git branch -M main

# Commit 1: ứng dụng + MySQL + phpMyAdmin + Nginx reverse proxy (bước 1-3)
git add .gitignore .env.example README.md docker-compose.yml backend frontend db nginx phpmyadmin scripts
git commit -m "feat: ứng dụng đặt vé FastAPI + React, MySQL, phpMyAdmin, Nginx reverse proxy HTTPS bằng Docker Compose"

# Commit 2: Prometheus + Grafana (bước 4)
git add docker-compose.monitoring.yml monitoring/prometheus monitoring/grafana/provisioning/dashboards \
        monitoring/grafana/provisioning/datasources/prometheus.yml monitoring/grafana/dashboards/cinema-overview.json
git commit -m "feat: giám sát bằng Prometheus, Grafana, cAdvisor, mysqld-exporter, nginx-exporter"

# Commit 3: Loki + Promtail (bước 5)
git add docker-compose.logging.yml monitoring/loki monitoring/promtail \
        monitoring/grafana/provisioning/datasources/loki.yml monitoring/grafana/dashboards/cinema-logs.json
git commit -m "feat: log tập trung Loki + Promtail, truy vấn LogQL"

# Commit 4: hardening (bước 6) và minh chứng
git add docker-compose.hardening.yml docs
git commit -m "feat: hardening container (read-only, cap_drop, giới hạn tài nguyên) và ảnh minh chứng"

git remote add origin https://github.com/<tài-khoản>/cinema-booking.git
git push -u origin main
```

Muốn mỗi commit tương ứng một hệ thống chạy được: trước mỗi commit, tạm thời chỉ giữ các file của những lớp đã commit trong thư mục (di chuyển file lớp sau ra ngoài), chạy `bash scripts/layers.sh && docker compose up -d`, kiểm tra rồi mới commit. Script `layers.sh` chỉ nạp các lớp `docker-compose.*.yml` đang có trong thư mục.

## 8. Sao lưu, khôi phục, kiểm thử

```bash
bash scripts/backup.sh                              # tạo backups/cinema_<thời gian>.sql và uploads_<thời gian>.tgz
bash scripts/restore.sh backups/cinema_xxx.sql      # khôi phục (hỏi xác nhận)
```

Kiểm thử tự động (không cần MySQL, dùng SQLite trong bộ nhớ):
```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt && pytest -q
```

## 9. Xử lý sự cố nhanh

| Triệu chứng | Kiểm tra |
|---|---|
| `docker compose` báo thiếu biến | Chạy `bash scripts/init.sh <IP>` để tạo `.env` |
| Cổng 80/443 đã bị dùng | Dừng dịch vụ cũ (`sudo systemctl stop nginx`) hoặc dùng `HTTP_PORT`, `HTTPS_PORT` |
| Backend không khởi động | `docker compose logs backend`; thường do MySQL chưa sẵn sàng hoặc sai mật khẩu |
| Đổi mật khẩu DB không có tác dụng | Script trong `db/init` chỉ chạy lần đầu; xóa volume: `docker compose down -v` |
| Grafana không thấy Loki | `docker compose restart grafana` |
| cAdvisor không lên | Thử thêm `privileged: true` cho `cadvisor` trong `docker-compose.monitoring.yml` |
| Cảnh báo chứng chỉ trên trình duyệt | Bình thường với chứng chỉ tự ký |
