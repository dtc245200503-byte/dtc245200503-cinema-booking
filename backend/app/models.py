from datetime import datetime

from sqlalchemy import (JSON, BigInteger, Boolean, CheckConstraint, DateTime,
                        ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('customer','admin')", name="ck_users_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(20))
    role: Mapped[str] = mapped_column(String(20), default="customer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (
        CheckConstraint("type IN ('movie','event')", name="ck_movies_type"),
        CheckConstraint("status IN ('showing','upcoming','ended')", name="ck_movies_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(10), default="movie")
    description: Mapped[str | None] = mapped_column(Text)
    duration_min: Mapped[int] = mapped_column(Integer)
    poster_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(10), default="showing")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    total_rows: Mapped[int] = mapped_column(Integer)
    total_cols: Mapped[int] = mapped_column(Integer)
    seats: Mapped[list["Seat"]] = relationship(back_populates="room", cascade="all, delete-orphan")


class Seat(Base):
    __tablename__ = "seats"
    __table_args__ = (
        UniqueConstraint("room_id", "row_label", "seat_number", name="uq_seat_position"),
        CheckConstraint("seat_type IN ('standard','vip')", name="ck_seats_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), index=True)
    row_label: Mapped[str] = mapped_column(String(3))
    seat_number: Mapped[int] = mapped_column(Integer)
    seat_type: Mapped[str] = mapped_column(String(10), default="standard")
    room: Mapped[Room] = relationship(back_populates="seats")


class Showtime(Base):
    __tablename__ = "showtimes"
    __table_args__ = (CheckConstraint("status IN ('open','cancelled')", name="ck_showtimes_status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    base_price: Mapped[int] = mapped_column(BigInteger)   # VND, số nguyên
    status: Mapped[str] = mapped_column(String(10), default="open")

    movie: Mapped[Movie] = relationship()
    room: Mapped[Room] = relationship()


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending_payment','paid','cancelled','refund_pending','refunded','expired')",
            name="ck_bookings_status"),
        Index("ix_bookings_status_expires", "status", "expires_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    showtime_id: Mapped[int] = mapped_column(ForeignKey("showtimes.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending_payment")
    total_amount: Mapped[int] = mapped_column(BigInteger)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship()
    showtime: Mapped[Showtime] = relationship()
    seats: Mapped[list["BookingSeat"]] = relationship(back_populates="booking", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="booking")
    refunds: Mapped[list["Refund"]] = relationship(back_populates="booking")


class BookingSeat(Base):
    """Chống đặt trùng ghế.

    MySQL không có partial unique index như PostgreSQL, nên dùng cột `active`:
    = 1 khi ghế đang bị giữ / đã bán, = NULL khi đã nhả. UNIQUE (showtime_id, seat_id, active)
    cho phép nhiều dòng NULL (ghế đã nhả, giữ lịch sử) nhưng chỉ một dòng active = 1.
    """
    __tablename__ = "booking_seats"
    __table_args__ = (
        UniqueConstraint("showtime_id", "seat_id", "active", name="uq_active_seat_per_showtime"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), index=True)
    showtime_id: Mapped[int] = mapped_column(ForeignKey("showtimes.id"))
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"))
    price: Mapped[int] = mapped_column(BigInteger)
    active: Mapped[int | None] = mapped_column(Integer, nullable=True, default=1)

    booking: Mapped[Booking] = relationship(back_populates="seats")
    seat: Mapped[Seat] = relationship()


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("method IN ('qr','wallet','card')", name="ck_payments_method"),
        CheckConstraint("status IN ('pending','success','failed')", name="ck_payments_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    method: Mapped[str] = mapped_column(String(10))
    amount: Mapped[int] = mapped_column(BigInteger)
    status: Mapped[str] = mapped_column(String(10), default="pending")
    transaction_code: Mapped[str] = mapped_column(String(64), unique=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    booking: Mapped[Booking] = relationship(back_populates="payments")


class Refund(Base):
    __tablename__ = "refunds"
    __table_args__ = (CheckConstraint("status IN ('pending','approved','rejected')", name="ck_refunds_status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"))
    amount: Mapped[int] = mapped_column(BigInteger)
    percent: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)
    reject_reason: Mapped[str | None] = mapped_column(String(500))
    processed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    booking: Mapped[Booking] = relationship(back_populates="refunds")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
