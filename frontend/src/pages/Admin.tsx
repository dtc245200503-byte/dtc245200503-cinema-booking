import { ChangeEvent, FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { api, checkPoster, fmtTime, POSTER_TYPES, STATUS_LABEL, upload, vnd } from "../api";
import PosterArt from "../components/PosterArt";
import type { AuditLog, Booking, Movie, Payment, Refund, Room, Showtime, Stats } from "../types";

const TABS = ["Thống kê", "Hoàn tiền", "Đơn đặt vé", "Giao dịch", "Phim / sự kiện", "Phòng & suất chiếu", "Nhật ký"] as const;
type Tab = (typeof TABS)[number];

function useLoad<T>(path: string, initial: T): [T, () => void, string] {
  const [data, setData] = useState<T>(initial);
  const [error, setError] = useState("");
  const reload = useCallback(() => {
    api<T>(path).then(setData).catch((e) => setError(e.message));
  }, [path]);
  useEffect(reload, [reload]);
  return [data, reload, error];
}

const Badge = ({ s }: { s: string }) => <span className={`badge ${s}`}>{STATUS_LABEL[s] ?? s}</span>;

export default function Admin() {
  const [tab, setTab] = useState<Tab>("Thống kê");
  return (
    <>
      <h1>Quản trị</h1>
      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? "active" : ""} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>
      {tab === "Thống kê" && <StatsTab />}
      {tab === "Hoàn tiền" && <RefundsTab />}
      {tab === "Đơn đặt vé" && <BookingsTab />}
      {tab === "Giao dịch" && <PaymentsTab />}
      {tab === "Phim / sự kiện" && <MoviesTab />}
      {tab === "Phòng & suất chiếu" && <ShowtimesTab />}
      {tab === "Nhật ký" && <AuditTab />}
    </>
  );
}

function StatsTab() {
  const [s, , err] = useLoad<Stats | null>("/admin/stats", null);
  if (err) return <p className="error">{err}</p>;
  if (!s) return <p className="muted">Đang tải…</p>;
  return (
    <>
      <div className="grid wide">
        <div className="panel stat"><div className="muted">Doanh thu</div><strong>{vnd(s.revenue)}</strong></div>
        <div className="panel stat"><div className="muted">Đã hoàn tiền</div><strong>{vnd(s.refunded)}</strong></div>
        <div className="panel stat"><div className="muted">Doanh thu thực (trừ hoàn tiền)</div><strong>{vnd(s.net)}</strong></div>
      </div>
      <h2>Số đơn theo trạng thái</h2>
      <table><tbody>
        {Object.entries(s.bookings_by_status).map(([k, v]) => <tr key={k}><td><Badge s={k} /></td><td>{v}</td></tr>)}
      </tbody></table>
      <h2>Doanh thu theo phim / sự kiện</h2>
      <table><tbody>
        {s.revenue_by_movie.map((m) => <tr key={m.title}><td>{m.title}</td><td>{vnd(m.revenue)}</td></tr>)}
      </tbody></table>
    </>
  );
}

function RefundsTab() {
  const [filter, setFilter] = useState("pending");
  const [rows, reload, err] = useLoad<Refund[]>(`/admin/refunds?status=${filter}`, []);
  async function act(r: Refund, approve: boolean) {
    try {
      if (approve) {
        if (!confirm(`Duyệt hoàn ${vnd(r.amount)} cho đơn #${r.booking_id}?`)) return;
        await api(`/admin/refunds/${r.id}/approve`, { method: "POST", body: {} });
      } else {
        const reason = prompt("Lý do từ chối:");
        if (!reason) return;
        await api(`/admin/refunds/${r.id}/reject`, { body: { reason } });
      }
      reload();
    } catch (e) { alert((e as Error).message); }
  }
  return (
    <>
      <select aria-label="Lọc trạng thái" value={filter} onChange={(e) => setFilter(e.target.value)}>
        <option value="pending">Chờ duyệt</option><option value="approved">Đã duyệt</option><option value="rejected">Từ chối</option>
      </select>
      {err && <p className="error">{err}</p>}
      <table>
        <thead><tr><th>#</th><th>Đơn</th><th>Số tiền</th><th>Tỉ lệ</th><th>Lý do</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>
          {rows.length === 0 && <tr><td colSpan={7} className="muted">Không có yêu cầu nào.</td></tr>}
          {rows.map((r) => (
            <tr key={r.id}>
              <td>{r.id}</td><td>#{r.booking_id}</td><td>{vnd(r.amount)}</td><td>{r.percent}%</td>
              <td>{r.reason ?? "—"}</td><td><Badge s={r.status} /></td>
              <td>{r.status === "pending" && (
                <div className="row">
                  <button onClick={() => act(r, true)}>Duyệt</button>
                  <button className="danger" onClick={() => act(r, false)}>Từ chối</button>
                </div>)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function BookingsTab() {
  const [filter, setFilter] = useState("");
  const [rows, , err] = useLoad<Booking[]>(`/admin/bookings${filter ? `?status=${filter}` : ""}`, []);
  return (
    <>
      <select aria-label="Lọc trạng thái" value={filter} onChange={(e) => setFilter(e.target.value)}>
        <option value="">Tất cả</option>
        {["pending_payment", "paid", "refund_pending", "refunded", "cancelled", "expired"].map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
      </select>
      {err && <p className="error">{err}</p>}
      <table>
        <thead><tr><th>#</th><th>Khách</th><th>Phim / suất</th><th>Ghế</th><th>Tổng</th><th>Trạng thái</th></tr></thead>
        <tbody>
          {rows.map((b) => (
            <tr key={b.id}>
              <td>{b.id}</td><td>{b.customer}</td>
              <td>{b.showtime.movie_title}<div className="muted">{fmtTime(b.showtime.start_time)}</div></td>
              <td>{b.seats.map((s) => s.label).join(", ")}</td><td>{vnd(b.total_amount)}</td><td><Badge s={b.status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function PaymentsTab() {
  const [rows, , err] = useLoad<Payment[]>("/admin/payments", []);
  return (
    <>
      {err && <p className="error">{err}</p>}
      <table>
        <thead><tr><th>#</th><th>Đơn</th><th>Phương thức</th><th>Số tiền</th><th>Trạng thái</th><th>Mã giao dịch</th></tr></thead>
        <tbody>
          {rows.map((p) => (
            <tr key={p.id}><td>{p.id}</td><td>#{p.booking_id}</td><td>{p.method}</td><td>{vnd(p.amount)}</td><td><Badge s={p.status} /></td><td>{p.transaction_code}</td></tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function MoviesTab() {
  const [rows, reload, err] = useLoad<Movie[]>("/movies", []);
  const empty = { title: "", type: "movie", description: "", duration_min: 120, status: "showing" };
  const [form, setForm] = useState(empty);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  // Giải phóng URL xem trước khi đổi ảnh hoặc rời trang
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  function pick(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setMsg(null);
    if (!f) { setFile(null); setPreview(null); return; }
    const problem = checkPoster(f);
    if (problem) {
      setMsg({ ok: false, text: problem });
      e.target.value = "";
      setFile(null); setPreview(null);
      return;
    }
    setFile(f);
    setPreview(URL.createObjectURL(f));
  }

  function clearFile() {
    setFile(null); setPreview(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  async function create(e: FormEvent) {
    e.preventDefault();
    setMsg(null); setBusy(true);
    try {
      const movie = await api<Movie>("/admin/movies", { body: { ...form, duration_min: Number(form.duration_min) } });
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        await upload<Movie>(`/admin/movies/${movie.id}/poster`, fd);
      }
      setMsg({ ok: true, text: `Đã thêm "${movie.title}"${file ? " kèm ảnh poster" : ""}.` });
      setForm(empty); clearFile(); reload();
    } catch (e2) {
      setMsg({ ok: false, text: (e2 as Error).message });
      reload();
    } finally { setBusy(false); }
  }

  async function changePoster(m: Movie, e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    const problem = checkPoster(f);
    if (problem) { setMsg({ ok: false, text: problem }); return; }
    try {
      const fd = new FormData();
      fd.append("file", f);
      await upload<Movie>(`/admin/movies/${m.id}/poster`, fd);
      setMsg({ ok: true, text: `Đã cập nhật ảnh poster của "${m.title}".` });
      reload();
    } catch (e2) { setMsg({ ok: false, text: (e2 as Error).message }); }
  }

  async function removePoster(m: Movie) {
    if (!confirm(`Xóa ảnh poster của "${m.title}"?`)) return;
    try {
      await api<Movie>(`/admin/movies/${m.id}/poster`, { method: "DELETE" });
      setMsg({ ok: true, text: `Đã xóa ảnh poster của "${m.title}".` });
      reload();
    } catch (e2) { setMsg({ ok: false, text: (e2 as Error).message }); }
  }

  async function setStatus(m: Movie, status: string) {
    try {
      await api(`/admin/movies/${m.id}`, { method: "PUT", body: { title: m.title, type: m.type, description: m.description, duration_min: m.duration_min, status } });
      reload();
    } catch (e2) { setMsg({ ok: false, text: (e2 as Error).message }); }
  }

  async function remove(m: Movie) {
    if (!confirm(`Xóa "${m.title}"?`)) return;
    try { await api(`/admin/movies/${m.id}`, { method: "DELETE" }); setMsg(null); reload(); }
    catch (e2) { setMsg({ ok: false, text: (e2 as Error).message }); }
  }

  return (
    <>
      <form className="panel" onSubmit={create}>
        <h2 style={{ marginTop: 0 }}>Thêm phim hoặc sự kiện</h2>
        <div className="form-grid">
          <label>Tên<input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label>
          <label>Loại
            <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}>
              <option value="movie">Phim</option><option value="event">Sự kiện</option>
            </select>
          </label>
          <label>Thời lượng (phút)
            <input type="number" min={1} max={600} required value={form.duration_min} onChange={(e) => setForm({ ...form, duration_min: Number(e.target.value) })} />
          </label>
          <label>Trạng thái
            <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
              {["showing", "upcoming", "ended"].map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
            </select>
          </label>
          <label className="wide">Mô tả
            <textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </label>
          <div className="wide row" style={{ alignItems: "flex-start" }}>
            {preview && <div className="preview"><PosterArt movie={{ title: form.title || "?", poster_url: preview }} /></div>}
            <div>
              <label className="file-btn btn secondary">
                {file ? "Chọn ảnh khác" : "Chọn ảnh poster"}
                <input ref={fileInput} className="visually-hidden" type="file" accept={POSTER_TYPES.join(",")} onChange={pick} />
              </label>
              <p className="hint" style={{ margin: "8px 0 0" }}>
                {file ? `${file.name} (${Math.ceil(file.size / 1024)} KB)` : "Ảnh JPG, PNG hoặc WEBP, tối đa 2 MB, nên dùng tỉ lệ đứng 2:3. Có thể bỏ qua và thêm sau."}
              </p>
              {file && <button type="button" className="secondary small" style={{ marginTop: 8 }} onClick={clearFile}>Bỏ ảnh</button>}
            </div>
          </div>
        </div>
        {msg && <p className={msg.ok ? "success" : "error"} role="alert" style={{ margin: "16px 0 0" }}>{msg.text}</p>}
        <div style={{ marginTop: 16 }}><button disabled={busy}>{busy ? "Đang lưu…" : "Thêm mới"}</button></div>
      </form>

      {err && <p className="error">{err}</p>}
      <table>
        <thead><tr><th>Ảnh</th><th>Tên</th><th>Loại</th><th>Trạng thái</th><th>Ảnh poster</th><th></th></tr></thead>
        <tbody>
          {rows.length === 0 && <tr><td colSpan={6} className="muted">Chưa có phim hoặc sự kiện nào.</td></tr>}
          {rows.map((m) => (
            <tr key={m.id}>
              <td className="thumb"><PosterArt movie={m} /></td>
              <td><strong>{m.title}</strong><div className="muted">{m.duration_min} phút</div></td>
              <td>{m.type === "movie" ? "Phim" : "Sự kiện"}</td>
              <td>
                <select aria-label={`Trạng thái của ${m.title}`} value={m.status} onChange={(e) => setStatus(m, e.target.value)}>
                  {["showing", "upcoming", "ended"].map((s) => <option key={s} value={s}>{STATUS_LABEL[s]}</option>)}
                </select>
              </td>
              <td>
                <div className="cell-actions">
                  <label className="file-btn btn secondary small">
                    {m.poster_url ? "Đổi ảnh" : "Thêm ảnh"}
                    <input className="visually-hidden" type="file" accept={POSTER_TYPES.join(",")} onChange={(e) => changePoster(m, e)} />
                  </label>
                  {m.poster_url && <button className="secondary small" onClick={() => removePoster(m)}>Xóa ảnh</button>}
                </div>
              </td>
              <td><button className="danger small" onClick={() => remove(m)}>Xóa</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function ShowtimesTab() {
  const [rooms, reloadRooms] = useLoad<Room[]>("/admin/rooms", []);
  const [movies] = useLoad<Movie[]>("/movies", []);
  const [shows, reloadShows, err] = useLoad<Showtime[]>("/admin/showtimes", []);
  const [room, setRoom] = useState({ name: "", total_rows: 8, total_cols: 10, vip_rows: 2 });
  const [st, setSt] = useState({ movie_id: 0, room_id: 0, start_time: "", base_price: 90000 });
  const [msg, setMsg] = useState("");

  async function addRoom(e: FormEvent) {
    e.preventDefault(); setMsg("");
    try { await api("/admin/rooms", { body: room }); reloadRooms(); setRoom({ ...room, name: "" }); }
    catch (e2) { setMsg((e2 as Error).message); }
  }
  async function addShow(e: FormEvent) {
    e.preventDefault(); setMsg("");
    try {
      await api("/admin/showtimes", { body: { ...st, start_time: new Date(st.start_time).toISOString() } });
      reloadShows();
    } catch (e2) { setMsg((e2 as Error).message); }
  }
  async function cancelShow(s: Showtime) {
    if (!confirm("Hủy suất chiếu này? Mọi vé đã bán sẽ được hoàn 100% tự động.")) return;
    try {
      const r = await api<{ refunded: number; cancelled: number }>(`/admin/showtimes/${s.id}/cancel`, { method: "POST", body: {} });
      alert(`Đã hoàn tiền ${r.refunded} vé, hủy ${r.cancelled} đơn chưa thanh toán.`);
      reloadShows();
    } catch (e) { alert((e as Error).message); }
  }

  return (
    <>
      <h2>Thêm phòng chiếu</h2>
      <form className="panel row" onSubmit={addRoom}>
        <label>Tên phòng<input required value={room.name} onChange={(e) => setRoom({ ...room, name: e.target.value })} /></label>
        <label>Số hàng<input type="number" min={1} max={26} value={room.total_rows} onChange={(e) => setRoom({ ...room, total_rows: Number(e.target.value) })} /></label>
        <label>Ghế mỗi hàng<input type="number" min={1} max={30} value={room.total_cols} onChange={(e) => setRoom({ ...room, total_cols: Number(e.target.value) })} /></label>
        <label>Số hàng VIP (cuối phòng)<input type="number" min={0} value={room.vip_rows} onChange={(e) => setRoom({ ...room, vip_rows: Number(e.target.value) })} /></label>
        <button style={{ alignSelf: "end" }}>Thêm phòng</button>
      </form>

      <h2>Thêm suất chiếu</h2>
      <form className="panel row" onSubmit={addShow}>
        <label>Phim / sự kiện<select required value={st.movie_id} onChange={(e) => setSt({ ...st, movie_id: Number(e.target.value) })}>
          <option value={0} disabled>Chọn…</option>{movies.map((m) => <option key={m.id} value={m.id}>{m.title}</option>)}</select></label>
        <label>Phòng<select required value={st.room_id} onChange={(e) => setSt({ ...st, room_id: Number(e.target.value) })}>
          <option value={0} disabled>Chọn…</option>{rooms.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}</select></label>
        <label>Giờ bắt đầu<input required type="datetime-local" value={st.start_time} onChange={(e) => setSt({ ...st, start_time: e.target.value })} /></label>
        <label>Giá vé thường (₫)<input type="number" min={1000} step={1000} value={st.base_price} onChange={(e) => setSt({ ...st, base_price: Number(e.target.value) })} /></label>
        <button style={{ alignSelf: "end" }}>Thêm suất</button>
      </form>
      {msg && <p className="error" role="alert">{msg}</p>}
      {err && <p className="error">{err}</p>}

      <table>
        <thead><tr><th>#</th><th>Phim</th><th>Phòng</th><th>Giờ chiếu</th><th>Giá</th><th>Trạng thái</th><th></th></tr></thead>
        <tbody>
          {shows.map((s) => (
            <tr key={s.id}>
              <td>{s.id}</td><td>{s.movie_title}</td><td>{s.room_name}</td><td>{fmtTime(s.start_time)}</td>
              <td>{vnd(s.base_price)}</td><td><Badge s={s.status === "open" ? "open" : "cancelled"} /></td>
              <td>{s.status === "open" && <button className="danger" onClick={() => cancelShow(s)}>Hủy suất</button>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

function AuditTab() {
  const [rows, , err] = useLoad<AuditLog[]>("/admin/audit-logs", []);
  return (
    <>
      {err && <p className="error">{err}</p>}
      <table>
        <thead><tr><th>Thời gian</th><th>Người dùng</th><th>Hành động</th><th>Đối tượng</th><th>Chi tiết</th></tr></thead>
        <tbody>
          {rows.map((l) => (
            <tr key={l.id}>
              <td>{fmtTime(l.created_at)}</td><td>{l.user_id ?? "—"}</td><td>{l.action}</td>
              <td>{l.entity_type} #{l.entity_id}</td><td><code>{l.detail ? JSON.stringify(l.detail) : ""}</code></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
