"""Nghiệp vụ đặt vé, thanh toán giả lập, hủy vé và hoàn tiền."""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (AuditLog, Booking, BookingSeat, Payment, Refund, Seat,
                        Showtime, User)


def now() -> datetime:
    return datetime.now(timezone.utc)


def aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def audit(db: Session, user_id: int | None, action: str, entity_type: str,
          entity_id: int | None, detail: dict | None = None) -> None:
    db.add(AuditLog(user_id=user_id, action=action, entity_type=entity_type,
                    entity_id=entity_id, detail=detail))


# ---------- Chính sách hoàn tiền ----------
def refund_percent(start_time: datetime, at: datetime | None = None) -> int | None:
    """>= 24h: 100%, >= 2h: 50%, còn lại: không cho hủy (None)."""
    remaining = aware(start_time) - (at or now())
    if remaining >= timedelta(hours=24):
        return 100
    if remaining >= timedelta(hours=2):
        return 50
    return None


# ---------- Ghế ----------
def release_seats(db: Session, booking_id: int) -> None:
    db.execute(update(BookingSeat).where(BookingSeat.booking_id == booking_id)
               .values(active=None))


def expire_overdue(db: Session) -> int:
    """Chuyển các đơn chờ thanh toán đã quá hạn sang 'expired' và nhả ghế."""
    ids = db.scalars(select(Booking.id).where(
        Booking.status == "pending_payment", Booking.expires_at < now())).all()
    for bid in ids:
        db.execute(update(Booking).where(Booking.id == bid).values(status="expired"))
        release_seats(db, bid)
    return len(ids)


# ---------- Đặt vé ----------
def create_booking(db: Session, user: User, showtime_id: int, seat_ids: list[int]) -> Booking:
    expire_overdue(db)
    db.commit()

    showtime = db.scalar(select(Showtime).where(Showtime.id == showtime_id).with_for_update())
    if showtime is None:
        raise HTTPException(404, "Không tìm thấy suất chiếu")
    if showtime.status != "open" or aware(showtime.start_time) <= now():
        raise HTTPException(400, "Suất chiếu không còn mở bán")

    seat_ids = sorted(set(seat_ids))
    if not seat_ids:
        raise HTTPException(400, "Chưa chọn ghế")
    if len(seat_ids) > settings.max_seats_per_booking:
        raise HTTPException(400, f"Tối đa {settings.max_seats_per_booking} ghế mỗi đơn")

    seats = db.scalars(select(Seat).where(Seat.id.in_(seat_ids),
                                          Seat.room_id == showtime.room_id)).all()
    if len(seats) != len(seat_ids):
        raise HTTPException(400, "Có ghế không thuộc phòng chiếu của suất này")

    taken = db.scalars(select(BookingSeat.seat_id).where(
        BookingSeat.showtime_id == showtime.id, BookingSeat.active == 1,
        BookingSeat.seat_id.in_(seat_ids))).all()
    if taken:
        raise HTTPException(409, "Ghế đã có người chọn, vui lòng chọn ghế khác")

    def price_of(seat: Seat) -> int:
        if seat.seat_type == "vip":
            return showtime.base_price * settings.vip_multiplier_percent // 100
        return showtime.base_price

    booking = Booking(user_id=user.id, showtime_id=showtime.id, status="pending_payment",
                      total_amount=sum(price_of(s) for s in seats),
                      expires_at=now() + timedelta(minutes=settings.hold_minutes))
    db.add(booking)
    try:
        db.flush()
        for s in seats:
            db.add(BookingSeat(booking_id=booking.id, showtime_id=showtime.id,
                               seat_id=s.id, price=price_of(s)))
        db.flush()
    except IntegrityError:  # lớp bảo vệ cuối: partial unique index
        db.rollback()
        raise HTTPException(409, "Ghế đã có người chọn, vui lòng chọn ghế khác")
    audit(db, user.id, "booking.create", "booking", booking.id, {"seats": seat_ids})
    db.commit()
    return booking


def _locked_booking(db: Session, booking_id: int, user: User) -> Booking:
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update())
    if booking is None or (booking.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Không tìm thấy đơn đặt vé")
    return booking


# ---------- Thanh toán giả lập ----------
def pay_booking(db: Session, user: User, booking_id: int, method: str,
                simulate_fail: bool = False) -> Payment:
    booking = _locked_booking(db, booking_id, user)
    if booking.status != "pending_payment":
        raise HTTPException(400, "Đơn không ở trạng thái chờ thanh toán")
    if aware(booking.expires_at) < now():
        expire_overdue(db)
        db.commit()
        raise HTTPException(410, "Đơn đã hết hạn giữ ghế")

    payment = Payment(booking_id=booking.id, method=method, amount=booking.total_amount,
                      transaction_code=uuid.uuid4().hex)
    if simulate_fail:
        payment.status = "failed"
    else:
        payment.status = "success"
        payment.paid_at = now()
        booking.status = "paid"
    db.add(payment)
    db.flush()
    audit(db, user.id, f"payment.{payment.status}", "payment", payment.id,
          {"booking_id": booking.id, "method": method})
    db.commit()
    return payment


# ---------- Khách hủy vé ----------
def cancel_booking(db: Session, user: User, booking_id: int, reason: str | None) -> Booking:
    booking = _locked_booking(db, booking_id, user)

    if booking.status == "pending_payment":
        booking.status = "cancelled"
        release_seats(db, booking.id)
        audit(db, user.id, "booking.cancel", "booking", booking.id)
        db.commit()
        return booking

    if booking.status != "paid":
        raise HTTPException(400, "Đơn này không thể hủy")

    showtime = db.get(Showtime, booking.showtime_id)
    percent = refund_percent(showtime.start_time)
    if percent is None:
        raise HTTPException(400, "Đã quá gần giờ chiếu (dưới 2 giờ), không thể hủy vé")

    payment = db.scalar(select(Payment).where(Payment.booking_id == booking.id,
                                              Payment.status == "success"))
    refund = Refund(booking_id=booking.id, payment_id=payment.id, percent=percent,
                    amount=payment.amount * percent // 100, reason=reason, status="pending")
    booking.status = "refund_pending"   # ghế vẫn giữ cho tới khi admin duyệt
    db.add(refund)
    db.flush()
    audit(db, user.id, "refund.request", "refund", refund.id,
          {"booking_id": booking.id, "percent": percent})
    db.commit()
    return booking


# ---------- Admin duyệt hoàn tiền ----------
def _pending_refund(db: Session, refund_id: int) -> Refund:
    refund = db.scalar(select(Refund).where(Refund.id == refund_id).with_for_update())
    if refund is None:
        raise HTTPException(404, "Không tìm thấy yêu cầu hoàn tiền")
    if refund.status != "pending":
        raise HTTPException(400, "Yêu cầu này đã được xử lý")
    return refund


def approve_refund(db: Session, admin: User, refund_id: int) -> Refund:
    refund = _pending_refund(db, refund_id)
    refund.status, refund.processed_by, refund.processed_at = "approved", admin.id, now()
    booking = db.get(Booking, refund.booking_id)
    booking.status = "refunded"
    release_seats(db, booking.id)
    audit(db, admin.id, "refund.approve", "refund", refund.id, {"amount": refund.amount})
    db.commit()
    return refund


def reject_refund(db: Session, admin: User, refund_id: int, reason: str) -> Refund:
    refund = _pending_refund(db, refund_id)
    refund.status, refund.reject_reason = "rejected", reason
    refund.processed_by, refund.processed_at = admin.id, now()
    db.get(Booking, refund.booking_id).status = "paid"   # vé vẫn còn hiệu lực
    audit(db, admin.id, "refund.reject", "refund", refund.id, {"reason": reason})
    db.commit()
    return refund


# ---------- Admin hủy suất chiếu: hoàn 100% hàng loạt ----------
def cancel_showtime(db: Session, admin: User, showtime_id: int) -> dict:
    showtime = db.scalar(select(Showtime).where(Showtime.id == showtime_id).with_for_update())
    if showtime is None:
        raise HTTPException(404, "Không tìm thấy suất chiếu")
    if showtime.status == "cancelled":
        raise HTTPException(400, "Suất chiếu đã được hủy trước đó")
    showtime.status = "cancelled"

    refunded = cancelled = 0
    bookings = db.scalars(select(Booking).where(
        Booking.showtime_id == showtime_id,
        Booking.status.in_(["pending_payment", "paid", "refund_pending"]))).all()
    for b in bookings:
        if b.status == "pending_payment":
            b.status = "cancelled"
            cancelled += 1
        else:
            payment = db.scalar(select(Payment).where(Payment.booking_id == b.id,
                                                      Payment.status == "success"))
            refund = db.scalar(select(Refund).where(Refund.booking_id == b.id,
                                                    Refund.status == "pending"))
            if refund is None:
                refund = Refund(booking_id=b.id, payment_id=payment.id)
                db.add(refund)
            refund.percent, refund.amount = 100, payment.amount
            refund.reason = "Suất chiếu bị hủy bởi quản trị viên"
            refund.status, refund.processed_by, refund.processed_at = "approved", admin.id, now()
            b.status = "refunded"
            refunded += 1
        release_seats(db, b.id)
    audit(db, admin.id, "showtime.cancel", "showtime", showtime.id,
          {"refunded": refunded, "cancelled": cancelled})
    db.commit()
    return {"refunded": refunded, "cancelled": cancelled}
