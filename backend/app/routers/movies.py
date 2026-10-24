from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models import BookingSeat, Movie, Seat, Showtime
from app.schemas import MovieOut, SeatMapOut, SeatOut, ShowtimeOut
from app.services.booking import expire_overdue, now

router = APIRouter(prefix="/api", tags=["catalog"])


def showtime_out(s: Showtime) -> ShowtimeOut:
    out = ShowtimeOut.model_validate(s)
    out.room_name, out.movie_title = s.room.name, s.movie.title
    return out


@router.get("/movies", response_model=list[MovieOut])
def list_movies(type: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    q = select(Movie).order_by(Movie.id.desc())
    if type:
        q = q.where(Movie.type == type)
    if status:
        q = q.where(Movie.status == status)
    return db.scalars(q).all()


@router.get("/movies/{movie_id}", response_model=MovieOut)
def get_movie(movie_id: int, db: Session = Depends(get_db)):
    movie = db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(404, "Không tìm thấy phim / sự kiện")
    return movie


@router.get("/movies/{movie_id}/showtimes", response_model=list[ShowtimeOut])
def movie_showtimes(movie_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(select(Showtime).where(
        Showtime.movie_id == movie_id, Showtime.status == "open",
        Showtime.start_time > now()).order_by(Showtime.start_time)).all()
    return [showtime_out(s) for s in rows]


@router.get("/showtimes/{showtime_id}/seats", response_model=SeatMapOut)
def seat_map(showtime_id: int, db: Session = Depends(get_db)):
    expire_overdue(db)
    db.commit()
    showtime = db.get(Showtime, showtime_id)
    if not showtime:
        raise HTTPException(404, "Không tìm thấy suất chiếu")
    seats = db.scalars(select(Seat).where(Seat.room_id == showtime.room_id)
                       .order_by(Seat.row_label, Seat.seat_number)).all()
    taken = set(db.scalars(select(BookingSeat.seat_id).where(
        BookingSeat.showtime_id == showtime_id, BookingSeat.active == 1)).all())
    vip_price = showtime.base_price * settings.vip_multiplier_percent // 100
    return SeatMapOut(
        showtime=showtime_out(showtime),
        seats=[SeatOut(id=s.id, row_label=s.row_label, seat_number=s.seat_number,
                       seat_type=s.seat_type, taken=s.id in taken,
                       price=vip_price if s.seat_type == "vip" else showtime.base_price)
               for s in seats])
