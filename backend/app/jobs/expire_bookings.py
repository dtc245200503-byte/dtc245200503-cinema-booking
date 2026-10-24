"""Chạy định kỳ (cron mỗi phút): hủy đơn quá hạn thanh toán và nhả ghế.
    python -m app.jobs.expire_bookings
"""
import logging

from app.db.session import SessionLocal
from app.services.booking import expire_overdue

log = logging.getLogger("expire_bookings")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

if __name__ == "__main__":
    with SessionLocal() as db:
        n = expire_overdue(db)
        db.commit()
    log.info("Đã hết hạn %d đơn", n)
