-- Lược đồ cơ sở dữ liệu (MySQL 8). Chạy tự động một lần khi volume dữ liệu còn trống.
SET NAMES utf8mb4;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  full_name VARCHAR(120) NOT NULL,
  phone VARCHAR(20) NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'customer',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_users_email (email),
  CONSTRAINT ck_users_role CHECK (role IN ('customer','admin'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE movies (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(200) NOT NULL,
  type VARCHAR(10) NOT NULL DEFAULT 'movie',
  description TEXT NULL,
  duration_min INT NOT NULL,
  poster_url VARCHAR(500) NULL,
  status VARCHAR(10) NOT NULL DEFAULT 'showing',
  CONSTRAINT ck_movies_type CHECK (type IN ('movie','event')),
  CONSTRAINT ck_movies_status CHECK (status IN ('showing','upcoming','ended'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE rooms (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  total_rows INT NOT NULL,
  total_cols INT NOT NULL,
  UNIQUE KEY uq_rooms_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE seats (
  id INT AUTO_INCREMENT PRIMARY KEY,
  room_id INT NOT NULL,
  row_label VARCHAR(3) NOT NULL,
  seat_number INT NOT NULL,
  seat_type VARCHAR(10) NOT NULL DEFAULT 'standard',
  UNIQUE KEY uq_seat_position (room_id, row_label, seat_number),
  CONSTRAINT fk_seats_room FOREIGN KEY (room_id) REFERENCES rooms (id) ON DELETE CASCADE,
  CONSTRAINT ck_seats_type CHECK (seat_type IN ('standard','vip'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE showtimes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  movie_id INT NOT NULL,
  room_id INT NOT NULL,
  start_time DATETIME NOT NULL,
  end_time DATETIME NOT NULL,
  base_price BIGINT NOT NULL,
  status VARCHAR(10) NOT NULL DEFAULT 'open',
  KEY ix_showtimes_start_time (start_time),
  CONSTRAINT fk_showtimes_movie FOREIGN KEY (movie_id) REFERENCES movies (id),
  CONSTRAINT fk_showtimes_room FOREIGN KEY (room_id) REFERENCES rooms (id),
  CONSTRAINT ck_showtimes_status CHECK (status IN ('open','cancelled'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  showtime_id INT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending_payment',
  total_amount BIGINT NOT NULL,
  expires_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_bookings_user_id (user_id),
  KEY ix_bookings_showtime_id (showtime_id),
  KEY ix_bookings_status_expires (status, expires_at),
  CONSTRAINT fk_bookings_user FOREIGN KEY (user_id) REFERENCES users (id),
  CONSTRAINT fk_bookings_showtime FOREIGN KEY (showtime_id) REFERENCES showtimes (id),
  CONSTRAINT ck_bookings_status CHECK (status IN
    ('pending_payment','paid','cancelled','refund_pending','refunded','expired'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Chống đặt trùng ghế: `active` = 1 khi ghế đang bị giữ/đã bán, NULL khi đã nhả.
-- UNIQUE cho phép nhiều NULL nên chỉ một dòng active = 1 cho mỗi (suất chiếu, ghế).
CREATE TABLE booking_seats (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  showtime_id INT NOT NULL,
  seat_id INT NOT NULL,
  price BIGINT NOT NULL,
  active TINYINT NULL DEFAULT 1,
  KEY ix_booking_seats_booking_id (booking_id),
  UNIQUE KEY uq_active_seat_per_showtime (showtime_id, seat_id, active),
  CONSTRAINT fk_bs_booking FOREIGN KEY (booking_id) REFERENCES bookings (id) ON DELETE CASCADE,
  CONSTRAINT fk_bs_showtime FOREIGN KEY (showtime_id) REFERENCES showtimes (id),
  CONSTRAINT fk_bs_seat FOREIGN KEY (seat_id) REFERENCES seats (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  method VARCHAR(10) NOT NULL,
  amount BIGINT NOT NULL,
  status VARCHAR(10) NOT NULL DEFAULT 'pending',
  transaction_code VARCHAR(64) NOT NULL,
  paid_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_payments_tx (transaction_code),
  KEY ix_payments_booking_id (booking_id),
  CONSTRAINT fk_payments_booking FOREIGN KEY (booking_id) REFERENCES bookings (id),
  CONSTRAINT ck_payments_method CHECK (method IN ('qr','wallet','card')),
  CONSTRAINT ck_payments_status CHECK (status IN ('pending','success','failed'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE refunds (
  id INT AUTO_INCREMENT PRIMARY KEY,
  booking_id INT NOT NULL,
  payment_id INT NOT NULL,
  amount BIGINT NOT NULL,
  percent INT NOT NULL,
  reason VARCHAR(500) NULL,
  status VARCHAR(10) NOT NULL DEFAULT 'pending',
  reject_reason VARCHAR(500) NULL,
  processed_by INT NULL,
  processed_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_refunds_booking_id (booking_id),
  KEY ix_refunds_status (status),
  CONSTRAINT fk_refunds_booking FOREIGN KEY (booking_id) REFERENCES bookings (id),
  CONSTRAINT fk_refunds_payment FOREIGN KEY (payment_id) REFERENCES payments (id),
  CONSTRAINT fk_refunds_admin FOREIGN KEY (processed_by) REFERENCES users (id),
  CONSTRAINT ck_refunds_status CHECK (status IN ('pending','approved','rejected'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE audit_logs (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  action VARCHAR(60) NOT NULL,
  entity_type VARCHAR(40) NOT NULL,
  entity_id INT NULL,
  detail JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
