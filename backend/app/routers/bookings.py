from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models import Booking, Payment, User
from app.routers.movies import showtime_out
from app.schemas import (BookingIn, BookingOut, BookingSeatOut, CancelIn,
                         PayIn, PaymentOut, RefundOut)
from app.services import booking as svc

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


def booking_out(b: Booking, with_customer: bool = False) -> BookingOut:
    refund = max(b.refunds, key=lambda r: r.id) if b.refunds else None
    return BookingOut(
        id=b.id, status=b.status, total_amount=b.total_amount,
        expires_at=b.expires_at, created_at=b.created_at,
        showtime=showtime_out(b.showtime),
        seats=[BookingSeatOut(seat_id=bs.seat_id, price=bs.price,
                              label=f"{bs.seat.row_label}{bs.seat.seat_number}")
               for bs in b.seats],
        refund=RefundOut.model_validate(refund) if refund else None,
        customer=b.user.full_name if with_customer else None)


@router.post("", response_model=BookingOut, status_code=201)
def create(data: BookingIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return booking_out(svc.create_booking(db, user, data.showtime_id, data.seat_ids))


@router.get("/mine", response_model=list[BookingOut])
def mine(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc.expire_overdue(db)
    db.commit()
    rows = db.scalars(select(Booking).where(Booking.user_id == user.id)
                      .order_by(Booking.id.desc())).all()
    return [booking_out(b) for b in rows]


@router.get("/{booking_id}", response_model=BookingOut)
def detail(booking_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = db.get(Booking, booking_id)
    if not b or (b.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Không tìm thấy đơn đặt vé")
    return booking_out(b)


@router.post("/{booking_id}/pay", response_model=PaymentOut)
def pay(booking_id: int, data: PayIn, user: User = Depends(get_current_user),
        db: Session = Depends(get_db)):
    return svc.pay_booking(db, user, booking_id, data.method, data.simulate_fail)


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel(booking_id: int, data: CancelIn, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    return booking_out(svc.cancel_booking(db, user, booking_id, data.reason))


@router.get("/{booking_id}/payments", response_model=list[PaymentOut])
def payments(booking_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    b = db.get(Booking, booking_id)
    if not b or (b.user_id != user.id and user.role != "admin"):
        raise HTTPException(404, "Không tìm thấy đơn đặt vé")
    return db.scalars(select(Payment).where(Payment.booking_id == booking_id)).all()
