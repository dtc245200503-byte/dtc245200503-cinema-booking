import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, fmtTime, STATUS_LABEL, vnd } from "../api";
import type { Booking } from "../types";

export default function MyBookings() {
  const [items, setItems] = useState<Booking[]>([]);
  const [error, setError] = useState("");

  const load = () => api<Booking[]>("/bookings/mine").then(setItems).catch((e) => setError(e.message));
  useEffect(() => { load(); }, []);

  async function cancel(b: Booking) {
    const paid = b.status === "paid";
    const note = paid
      ? "Hủy vé đã thanh toán sẽ tạo yêu cầu hoàn tiền (hoàn 100% nếu còn từ 24 giờ, 50% nếu còn từ 2 giờ). Tiếp tục?"
      : "Hủy đơn này?";
    if (!confirm(note)) return;
    const reason = paid ? prompt("Lý do hủy (không bắt buộc):") ?? undefined : undefined;
    try {
      await api(`/bookings/${b.id}/cancel`, { body: { reason } });
      await load();
    } catch (e) { alert((e as Error).message); }
  }

  return (
    <>
      <h1>Vé của tôi</h1>
      {error && <p className="error">{error}</p>}
      {!error && items.length === 0 && <p className="muted">Bạn chưa đặt vé nào. <Link to="/">Xem phim và sự kiện</Link></p>}
      {items.map((b) => (
        <div className="ticket" key={b.id}>
          <div className="ticket-main">
            <div className="title">{b.showtime.movie_title}</div>
            <div className="muted">{fmtTime(b.showtime.start_time)} · {b.showtime.room_name}</div>
            <p style={{ margin: ".5rem 0 0" }}>Ghế {b.seats.map((s) => s.label).join(", ")} · Mã vé #{b.id}</p>
            {b.refund && (
              <p style={{ margin: ".5rem 0 0" }}>
                Hoàn tiền {vnd(b.refund.amount)} ({b.refund.percent}%) <span className={`badge ${b.refund.status}`}>{STATUS_LABEL[b.refund.status]}</span>
                {b.refund.reject_reason && <span className="error"> · Lý do từ chối: {b.refund.reject_reason}</span>}
              </p>
            )}
          </div>
          <div className="ticket-stub">
            <span className={`badge ${b.status}`}>{STATUS_LABEL[b.status]}</span>
            <span className="price">{vnd(b.total_amount)}</span>
            {b.status === "pending_payment" && <Link className="btn" to={`/checkout/${b.id}`}>Thanh toán</Link>}
            {(b.status === "pending_payment" || b.status === "paid") && (
              <button className="secondary" onClick={() => cancel(b)}>Hủy</button>
            )}
          </div>
        </div>
      ))}
    </>
  );
}
