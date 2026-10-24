"""Tạo dữ liệu mẫu khi bảng users còn trống (chạy tự động lúc container backend khởi động).

Mật khẩu lấy từ biến môi trường ADMIN_PASSWORD / DEMO_PASSWORD (do scripts/init.sh sinh ngẫu nhiên).
Tài khoản DB của ứng dụng chỉ có quyền SELECT/INSERT/UPDATE/DELETE nên script chỉ dùng DML.
"""
import os
import secrets
from datetime import timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import Movie, Room, Seat, Showtime, User
from app.services.booking import now


def main() -> None:
    admin_pw = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(12)
    demo_pw = os.environ.get("DEMO_PASSWORD") or secrets.token_urlsafe(12)
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == "admin@cinema.local")):
            print("Dữ liệu mẫu đã tồn tại, bỏ qua.")
            return
        db.add_all([
            User(email="admin@cinema.local", password_hash=hash_password(admin_pw),
                 full_name="Quản trị viên", role="admin"),
            User(email="khach@cinema.local", password_hash=hash_password(demo_pw),
                 full_name="Khách hàng mẫu", role="customer"),
        ])
        room = Room(name="Phòng 1", total_rows=8, total_cols=10)
        db.add(room)
        db.flush()
        for r in range(8):
            for c in range(1, 11):
                db.add(Seat(room_id=room.id, row_label=chr(65 + r), seat_number=c,
                            seat_type="vip" if r >= 6 else "standard"))
        movies = [Movie(title="Mưa đỏ", type="movie", duration_min=124, status="showing",
                        description="Phim chiếu rạp mẫu."),
                  Movie(title="Đêm nhạc acoustic", type="event", duration_min=120, status="showing",
                        description="Sự kiện âm nhạc mẫu.")]
        db.add_all(movies)
        db.flush()
        base = now().replace(minute=0, second=0, microsecond=0) + timedelta(days=2, hours=1)
        for i, m in enumerate(movies):
            for d in range(3):
                start = base + timedelta(days=d, hours=i * 3)
                db.add(Showtime(movie_id=m.id, room_id=room.id, start_time=start,
                                end_time=start + timedelta(minutes=m.duration_min),
                                base_price=90000))
        db.commit()
        print("Đã tạo dữ liệu mẫu: admin@cinema.local, khach@cinema.local")


if __name__ == "__main__":
    main()
