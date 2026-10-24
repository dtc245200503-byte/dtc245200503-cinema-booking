import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, fmtTime, STATUS_LABEL, vnd } from "../api";
import type { Booking, Payment } from "../types";

export default function Checkout() {
  const { id } = useParams();
  const [booking, setBooking] = useState<Booking | null>(null);
  const [method, setMethod] = useState("qr");
  const [fail, setFail] = useState(false);
  const [left, setLeft] = useState(0);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [paid, setPaid] = useState<Payment | null>(null);

  const load = () => api<Booking>(`/bookings/${id}`).then(setBooking).catch((e) => setMsg({ ok: false, text: e.message }));
  useEffect(() => { load(); }, [id]);

  useEffect(() => {
    if (!booking || booking.status !== "pending_payment") return;
    const tick = () => setLeft(Math.max(0, Math.floor((new Date(booking.expires_at).getTime() - Date.now()) / 1000)));
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [booking]);

  async function pay() {
    setBusy(true); setMsg(null);
    try {
      const p = await api<Payment>(`/bookings/${id}/pay`, { body: { method, simulate_fail: fail } });
      if (p.status === "success") setPaid(p);
      else setMsg({ ok: false, text: "Thanh toán thất bại (giả lập). Bạn có thể thử lại khi còn thời gian giữ ghế." });
      await load();
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
      await load();
    } finally { setBusy(false); }
  }

  if (!booking) return msg ? <p className="error">{msg.text}</p> : <p className="muted">Đang tải…</p>;
  const mm = String(Math.floor(left / 60)).padStart(2, "0"), ss = String(left % 60).padStart(2, "0");

  return (
    <>
      <h1>Thanh toán đơn #{booking.id}</h1>
      <div className="ticket">
        <div className="ticket-main">
          <div className="title">{booking.showtime.movie_title}</div>
          <div className="muted">{fmtTime(booking.showtime.start_time)} · {booking.showtime.room_name}</div>
          <p style={{ margin: ".5rem 0 0" }}>Ghế {booking.seats.map((s) => s.label).join(", ")}</p>
        </div>
        <div className="ticket-stub">
          <span className={`badge ${booking.status}`}>{STATUS_LABEL[booking.status]}</span>
          <span className="price">{vnd(booking.total_amount)}</span>
        </div>
      </div>

      {booking.status === "pending_payment" && (
        <div className="panel">
          <p>Ghế được giữ trong: <span className={`countdown ${left < 60 ? "low" : ""}`}>{mm}:{ss}</span></p>
          <div className="row">
            <label>Phương thức
              <select value={method} onChange={(e) => setMethod(e.target.value)}>
                <option value="qr">Chuyển khoản / QR</option>
                <option value="wallet">Ví điện tử</option>
                <option value="card">Thẻ</option>
              </select>
            </label>
            <label className="row" style={{ marginTop: "1.2rem" }}>
              <input type="checkbox" checked={fail} onChange={(e) => setFail(e.target.checked)} />
              Giả lập thanh toán thất bại (để demo)
            </label>
          </div>
          {msg && <p className={msg.ok ? "success" : "error"} role="alert">{msg.text}</p>}
          <button disabled={busy || left === 0} onClick={pay}>Thanh toán {vnd(booking.total_amount)}</button>
        </div>
      )}

      {booking.status === "paid" && (
        <div className="panel">
          <p className="success"><strong>Thanh toán thành công.</strong> Mã vé: #{booking.id}{paid && <> · Mã giao dịch: {paid.transaction_code}</>}</p>
          <Link className="btn" to="/my-bookings">Xem vé của tôi</Link>
        </div>
      )}
      {booking.status === "expired" && (
        <div className="panel"><p className="error">Đơn đã hết hạn giữ ghế.</p><Link className="btn" to="/">Chọn lại suất chiếu</Link></div>
      )}
    </>
  );
}
