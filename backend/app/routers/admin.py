import uuid
from datetime import timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import require_admin
from app.db.session import get_db
from app.models import (AuditLog, Booking, Movie, Payment, Refund, Room, Seat,
                        Showtime, User)
from app.routers.bookings import booking_out
from app.routers.movies import showtime_out
from app.schemas import (AuditOut, BookingOut, MovieIn, MovieOut, PaymentOut,
                         RefundOut, RejectIn, RoomIn, RoomOut, ShowtimeIn, ShowtimeOut)
from app.services import booking as svc

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ----- Phim / sự kiện -----
@router.post("/movies", response_model=MovieOut, status_code=201)
def create_movie(data: MovieIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = Movie(**data.model_dump())
    db.add(m)
    db.flush()
    svc.audit(db, admin.id, "movie.create", "movie", m.id)
    db.commit()
    return m


@router.put("/movies/{movie_id}", response_model=MovieOut)
def update_movie(movie_id: int, data: MovieIn, admin: User = Depends(require_admin),
                 db: Session = Depends(get_db)):
    m = db.get(Movie, movie_id)
    if not m:
        raise HTTPException(404, "Không tìm thấy phim / sự kiện")
    for k, v in data.model_dump().items():
        setattr(m, k, v)
    svc.audit(db, admin.id, "movie.update", "movie", m.id)
    db.commit()
    return m


@router.delete("/movies/{movie_id}", status_code=204)
def delete_movie(movie_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = db.get(Movie, movie_id)
    if not m:
        raise HTTPException(404, "Không tìm thấy phim / sự kiện")
    poster = m.poster_url
    try:
        db.delete(m)
        svc.audit(db, admin.id, "movie.delete", "movie", movie_id)
        db.commit()
        _remove_poster_file(poster)
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "Phim đã có suất chiếu, hãy chuyển trạng thái sang 'ended' thay vì xóa")


# ----- Ảnh poster -----
def _detect_image_ext(head: bytes) -> str | None:
    """Nhận diện định dạng theo nội dung file (không tin tên file hay Content-Type do client gửi)."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


def _poster_dir() -> Path:
    d = Path(settings.upload_dir) / "posters"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _remove_poster_file(url: str | None) -> None:
    if url and url.startswith("/uploads/posters/"):
        (Path(settings.upload_dir) / "posters" / Path(url).name).unlink(missing_ok=True)


@router.post("/movies/{movie_id}/poster", response_model=MovieOut)
def upload_poster(movie_id: int, file: UploadFile = File(...),
                  admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = db.get(Movie, movie_id)
    if not m:
        raise HTTPException(404, "Không tìm thấy phim / sự kiện")
    data = file.file.read(settings.max_poster_bytes + 1)
    if len(data) > settings.max_poster_bytes:
        raise HTTPException(413, f"Ảnh quá lớn, tối đa {settings.max_poster_bytes // (1024 * 1024)} MB")
    ext = _detect_image_ext(data[:16])
    if ext is None:
        raise HTTPException(415, "Chỉ chấp nhận ảnh JPG, PNG hoặc WEBP")
    name = f"{uuid.uuid4().hex}.{ext}"          # tên ngẫu nhiên: không dùng tên file của client
    (_poster_dir() / name).write_bytes(data)
    _remove_poster_file(m.poster_url)
    m.poster_url = f"/uploads/posters/{name}"
    svc.audit(db, admin.id, "movie.poster", "movie", m.id, {"file": name, "bytes": len(data)})
    db.commit()
    return m


@router.delete("/movies/{movie_id}/poster", response_model=MovieOut)
def delete_poster(movie_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    m = db.get(Movie, movie_id)
    if not m:
        raise HTTPException(404, "Không tìm thấy phim / sự kiện")
    _remove_poster_file(m.poster_url)
    m.poster_url = None
    svc.audit(db, admin.id, "movie.poster_delete", "movie", m.id)
    db.commit()
    return m


# ----- Phòng chiếu -----
@router.get("/rooms", response_model=list[RoomOut])
def list_rooms(db: Session = Depends(get_db)):
    return db.scalars(select(Room).order_by(Room.id)).all()


@router.post("/rooms", response_model=RoomOut, status_code=201)
def create_room(data: RoomIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if db.scalar(select(Room).where(Room.name == data.name)):
        raise HTTPException(409, "Tên phòng đã tồn tại")
    room = Room(name=data.name, total_rows=data.total_rows, total_cols=data.total_cols)
    db.add(room)
    db.flush()
    for r in range(data.total_rows):
        is_vip = r >= data.total_rows - data.vip_rows
        for c in range(1, data.total_cols + 1):
            db.add(Seat(room_id=room.id, row_label=chr(65 + r), seat_number=c,
                        seat_type="vip" if is_vip else "standard"))
    svc.audit(db, admin.id, "room.create", "room", room.id)
    db.commit()
    return room


# ----- Suất chiếu -----
@router.get("/showtimes", response_model=list[ShowtimeOut])
def list_showtimes(db: Session = Depends(get_db)):
    rows = db.scalars(select(Showtime).order_by(Showtime.start_time.desc()).limit(200)).all()
    return [showtime_out(s) for s in rows]


@router.post("/showtimes", response_model=ShowtimeOut, status_code=201)
def create_showtime(data: ShowtimeIn, admin: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    movie, room = db.get(Movie, data.movie_id), db.get(Room, data.room_id)
    if not movie or not room:
        raise HTTPException(404, "Phim hoặc phòng không tồn tại")
    start = data.start_time if data.start_time.tzinfo else data.start_time.replace(tzinfo=timezone.utc)
    start = start.astimezone(timezone.utc)
    end = start + timedelta(minutes=movie.duration_min)
    clash = db.scalar(select(Showtime.id).where(
        Showtime.room_id == room.id, Showtime.status == "open",
        Showtime.start_time < end, Showtime.end_time > start))
    if clash:
        raise HTTPException(409, "Phòng đã có suất chiếu trùng giờ")
    s = Showtime(movie_id=movie.id, room_id=room.id, start_time=start,
                 end_time=end, base_price=data.base_price)
    db.add(s)
    db.flush()
    svc.audit(db, admin.id, "showtime.create", "showtime", s.id)
    db.commit()
    return showtime_out(s)


@router.post("/showtimes/{showtime_id}/cancel")
def cancel_showtime(showtime_id: int, admin: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    return svc.cancel_showtime(db, admin, showtime_id)


# ----- Đơn, giao dịch, hoàn tiền -----
@router.get("/bookings", response_model=list[BookingOut])
def list_bookings(status: str | None = None, db: Session = Depends(get_db)):
    q = select(Booking).order_by(Booking.id.desc()).limit(300)
    if status:
        q = q.where(Booking.status == status)
    return [booking_out(b, with_customer=True) for b in db.scalars(q).all()]


@router.get("/payments", response_model=list[PaymentOut])
def list_payments(status: str | None = None, db: Session = Depends(get_db)):
    q = select(Payment).order_by(Payment.id.desc()).limit(300)
    if status:
        q = q.where(Payment.status == status)
    return db.scalars(q).all()


@router.get("/refunds", response_model=list[RefundOut])
def list_refunds(status: str | None = None, db: Session = Depends(get_db)):
    q = select(Refund).order_by(Refund.id.desc()).limit(300)
    if status:
        q = q.where(Refund.status == status)
    return db.scalars(q).all()


@router.post("/refunds/{refund_id}/approve", response_model=RefundOut)
def approve(refund_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return svc.approve_refund(db, admin, refund_id)


@router.post("/refunds/{refund_id}/reject", response_model=RefundOut)
def reject(refund_id: int, data: RejectIn, admin: User = Depends(require_admin),
           db: Session = Depends(get_db)):
    return svc.reject_refund(db, admin, refund_id, data.reason)


# ----- Thống kê, nhật ký -----
@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    revenue = db.scalar(select(func.coalesce(func.sum(Payment.amount), 0))
                        .where(Payment.status == "success")) or 0
    refunded = db.scalar(select(func.coalesce(func.sum(Refund.amount), 0))
                         .where(Refund.status == "approved")) or 0
    by_status = dict(db.execute(select(Booking.status, func.count()).group_by(Booking.status)).all())
    per_movie = db.execute(
        select(Movie.title, func.coalesce(func.sum(Payment.amount), 0))
        .join(Showtime, Showtime.movie_id == Movie.id)
        .join(Booking, Booking.showtime_id == Showtime.id)
        .join(Payment, Payment.booking_id == Booking.id)
        .where(Payment.status == "success").group_by(Movie.title)
        .order_by(func.sum(Payment.amount).desc()).limit(10)).all()
    return {"revenue": int(revenue), "refunded": int(refunded), "net": int(revenue - refunded),
            "bookings_by_status": by_status,
            "revenue_by_movie": [{"title": t, "revenue": int(v)} for t, v in per_movie]}


@router.get("/audit-logs", response_model=list[AuditOut])
def audit_logs(db: Session = Depends(get_db)):
    return db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(200)).all()
