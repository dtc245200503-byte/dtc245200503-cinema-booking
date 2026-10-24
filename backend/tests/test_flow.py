"""Kiểm thử luồng chính trên SQLite trong bộ nhớ.
Chạy:  cd backend && pytest -q
"""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models import Base, Movie, Room, Seat, Showtime, User
from app.services.booking import now, refund_percent


def test_refund_policy():
    t = now()
    assert refund_percent(t + timedelta(hours=30), t) == 100
    assert refund_percent(t + timedelta(hours=5), t) == 50
    assert refund_percent(t + timedelta(minutes=90), t) is None


@pytest.fixture()
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as db:
        db.add_all([User(email="admin@t.vn", password_hash=hash_password("secret123"),
                         full_name="Admin", role="admin")])
        room = Room(name="P1", total_rows=2, total_cols=3)
        db.add(room)
        db.flush()
        for r in "AB":
            for c in (1, 2, 3):
                db.add(Seat(room_id=room.id, row_label=r, seat_number=c))
        m = Movie(title="Phim thử", duration_min=100)
        db.add(m)
        db.flush()
        start = now() + timedelta(days=3)
        db.add(Showtime(movie_id=m.id, room_id=room.id, start_time=start,
                        end_time=start + timedelta(minutes=100), base_price=100000))
        db.commit()

    def override():
        with Session() as s:
            yield s

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def auth(client, email, password="secret123", register=False):
    if register:
        r = client.post("/api/auth/register",
                        json={"email": email, "password": password, "full_name": email})
    else:
        r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_booking_payment_refund_flow(client):
    a = auth(client, "a@t.vn", register=True)
    b = auth(client, "b@t.vn", register=True)
    admin = auth(client, "admin@t.vn")

    seats = client.get("/api/showtimes/1/seats").json()["seats"]
    s1, s2 = seats[0]["id"], seats[1]["id"]

    r = client.post("/api/bookings", json={"showtime_id": 1, "seat_ids": [s1, s2]}, headers=a)
    assert r.status_code == 201 and r.json()["total_amount"] == 200000
    bid = r.json()["id"]

    # người thứ hai chọn trùng ghế -> 409
    r = client.post("/api/bookings", json={"showtime_id": 1, "seat_ids": [s2]}, headers=b)
    assert r.status_code == 409

    assert client.post(f"/api/bookings/{bid}/pay", json={"method": "qr"}, headers=a).status_code == 200

    r = client.post(f"/api/bookings/{bid}/cancel", json={"reason": "bận"}, headers=a)
    assert r.json()["status"] == "refund_pending" and r.json()["refund"]["percent"] == 100

    # khách thường không được vào API admin
    assert client.get("/api/admin/refunds", headers=a).status_code == 403

    rid = r.json()["refund"]["id"]
    assert client.post(f"/api/admin/refunds/{rid}/approve", headers=admin).status_code == 200

    # ghế đã được nhả
    r = client.post("/api/bookings", json={"showtime_id": 1, "seat_ids": [s2]}, headers=b)
    assert r.status_code == 201

    stats = client.get("/api/admin/stats", headers=admin).json()
    assert stats["revenue"] == 200000 and stats["refunded"] == 200000 and stats["net"] == 0


def test_poster_upload(client, tmp_path, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    admin = auth(client, "admin@t.vn")
    user = auth(client, "u@t.vn", register=True)

    png = b"\x89PNG\r\n\x1a\n" + b"0" * 64
    # khách thường không được tải ảnh
    r = client.post("/api/admin/movies/1/poster", files={"file": ("a.png", png, "image/png")}, headers=user)
    assert r.status_code == 403
    # file không phải ảnh bị từ chối dù đặt đuôi .png
    r = client.post("/api/admin/movies/1/poster", files={"file": ("a.png", b"<html>", "image/png")}, headers=admin)
    assert r.status_code == 415
    # ảnh hợp lệ
    r = client.post("/api/admin/movies/1/poster", files={"file": ("a.png", png, "image/png")}, headers=admin)
    assert r.status_code == 200 and r.json()["poster_url"].startswith("/uploads/posters/")
    name = r.json()["poster_url"].rsplit("/", 1)[1]
    assert (tmp_path / "posters" / name).exists()
    # xóa ảnh
    r = client.delete("/api/admin/movies/1/poster", headers=admin)
    assert r.json()["poster_url"] is None and not (tmp_path / "posters" / name).exists()
