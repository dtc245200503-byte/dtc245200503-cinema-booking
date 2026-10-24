import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, fmtTime, vnd } from "../api";
import type { Booking, Seat, SeatMap } from "../types";

export default function SeatPicker() {
  const { id } = useParams();
  const nav = useNavigate();
  const [map, setMap] = useState<SeatMap | null>(null);
  const [picked, setPicked] = useState<number[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api<SeatMap>(`/showtimes/${id}/seats`).then(setMap).catch((e) => setError(e.message));
  }, [id]);
  useEffect(load, [load]);

  const rows = useMemo(() => {
    const r = new Map<string, Seat[]>();
    map?.seats.forEach((s) => r.set(s.row_label, [...(r.get(s.row_label) ?? []), s]));
    return [...r.entries()];
  }, [map]);

  const total = map?.seats.filter((s) => picked.includes(s.id)).reduce((a, s) => a + s.price, 0) ?? 0;
  const toggle = (s: Seat) =>
    setPicked((p) => (p.includes(s.id) ? p.filter((x) => x !== s.id) : [...p, s.id]));

  async function hold() {
    setError(""); setBusy(true);
    try {
      const b = await api<Booking>("/bookings", { body: { showtime_id: Number(id), seat_ids: picked } });
      nav(`/checkout/${b.id}`);
    } catch (e) {
      setError((e as Error).message);
      setPicked([]);
      load();   // làm mới sơ đồ để thấy ghế vừa bị người khác chọn
    } finally { setBusy(false); }
  }

  if (!map) return error ? <p className="error">{error}</p> : <p className="muted">Đang tải…</p>;

  return (
    <>
      <h1>{map.showtime.movie_title}</h1>
      <p className="muted">{fmtTime(map.showtime.start_time)} · {map.showtime.room_name}</p>
      <div className="panel">
        <div className="screen">Màn hình / Sân khấu</div>
        <div className="seatmap">
          {rows.map(([label, seats]) => (
            <div className="seatrow" key={label}>
              <span className="rowlabel">{label}</span>
              {seats.map((s, i) => (
                <button key={s.id} disabled={s.taken}
                  aria-pressed={picked.includes(s.id)}
                  aria-label={`Ghế ${label}${s.seat_number}${s.taken ? ", đã có người chọn" : ""}`}
                  className={`seat ${i === Math.floor(seats.length / 2) - 1 ? "aisle" : ""} ${s.seat_type === "vip" ? "vip" : ""} ${picked.includes(s.id) ? "selected" : ""} ${s.taken ? "taken" : ""}`}
                  onClick={() => toggle(s)}>
                  {s.seat_number}
                </button>
              ))}
            </div>
          ))}
        </div>
        <div className="legend">
          <span><i />Ghế thường</span><span><i className="vip" />Ghế VIP</span>
          <span><i className="sel" />Đang chọn</span><span><i className="tk" />Đã có người chọn</span>
        </div>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="summary-bar">
        <div>
          {picked.length > 0
            ? <>Đã chọn {picked.length} ghế · <strong>{vnd(total)}</strong></>
            : <span className="muted">Chọn ghế để tiếp tục</span>}
        </div>
        <button disabled={picked.length === 0 || busy} onClick={hold}>Giữ ghế và thanh toán</button>
      </div>
    </>
  );
}
