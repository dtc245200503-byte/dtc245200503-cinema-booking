import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.routers import admin, auth, bookings, movies

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Cinema Booking API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["*"], allow_headers=["*"])

# Số liệu cho Prometheus (/metrics chỉ truy cập được nội bộ, Nginx không chuyển tiếp đường dẫn này)
Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(
    app, endpoint="/metrics", include_in_schema=False)

for r in (auth.router, movies.router, bookings.router, admin.router):
    app.include_router(r)


@app.get("/api/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    """Dùng cho giám sát: kiểm tra ứng dụng và kết nối CSDL."""
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "up"}
