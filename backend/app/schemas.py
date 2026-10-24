from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field


def _to_utc(v: datetime) -> datetime:
    """MySQL trả datetime không múi giờ (đã lưu theo UTC): gắn UTC để trình duyệt hiểu đúng."""
    return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v.astimezone(timezone.utc)


UTCDateTime = Annotated[datetime, AfterValidator(_to_utc)]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ----- Auth -----
class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str = Field(min_length=1, max_length=120)
    phone: str | None = None


class LoginIn(BaseModel):
    email: str   # không kiểm tra định dạng chặt khi đăng nhập (tài khoản mẫu dùng đuôi .local)
    password: str


class UserOut(ORM):
    id: int
    email: str
    full_name: str
    phone: str | None
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ----- Phim / suất chiếu -----
class MovieIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    type: str = Field(default="movie", pattern="^(movie|event)$")
    description: str | None = None
    duration_min: int = Field(gt=0, le=600)
    status: str = Field(default="showing", pattern="^(showing|upcoming|ended)$")


class MovieOut(MovieIn, ORM):
    id: int
    poster_url: str | None = None   # chỉ do hệ thống gán sau khi tải ảnh lên


class ShowtimeOut(ORM):
    id: int
    movie_id: int
    room_id: int
    start_time: UTCDateTime
    end_time: UTCDateTime
    base_price: int
    status: str
    room_name: str | None = None
    movie_title: str | None = None


class SeatOut(BaseModel):
    id: int
    row_label: str
    seat_number: int
    seat_type: str
    price: int
    taken: bool


class SeatMapOut(BaseModel):
    showtime: ShowtimeOut
    seats: list[SeatOut]


# ----- Đặt vé -----
class BookingIn(BaseModel):
    showtime_id: int
    seat_ids: list[int]


class PayIn(BaseModel):
    method: str = Field(pattern="^(qr|wallet|card)$")
    simulate_fail: bool = False   # giả lập thanh toán thất bại để demo


class CancelIn(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class BookingSeatOut(BaseModel):
    seat_id: int
    label: str
    price: int


class RefundOut(ORM):
    id: int
    booking_id: int
    amount: int
    percent: int
    reason: str | None
    status: str
    reject_reason: str | None
    created_at: UTCDateTime
    processed_at: UTCDateTime | None


class BookingOut(BaseModel):
    id: int
    status: str
    total_amount: int
    expires_at: UTCDateTime
    created_at: UTCDateTime
    showtime: ShowtimeOut
    seats: list[BookingSeatOut]
    refund: RefundOut | None = None
    customer: str | None = None


class PaymentOut(ORM):
    id: int
    booking_id: int
    method: str
    amount: int
    status: str
    transaction_code: str
    paid_at: UTCDateTime | None


# ----- Admin -----
class RoomIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    total_rows: int = Field(ge=1, le=26)
    total_cols: int = Field(ge=1, le=30)
    vip_rows: int = Field(default=0, ge=0)   # N hàng cuối là ghế VIP


class RoomOut(ORM):
    id: int
    name: str
    total_rows: int
    total_cols: int


class ShowtimeIn(BaseModel):
    movie_id: int
    room_id: int
    start_time: UTCDateTime
    base_price: int = Field(gt=0)


class RejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class AuditOut(ORM):
    id: int
    user_id: int | None
    action: str
    entity_type: str
    entity_id: int | None
    detail: dict | None
    created_at: UTCDateTime
