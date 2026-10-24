import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, STATUS_LABEL, vnd } from "../api";
import PosterArt from "../components/PosterArt";
import type { Movie, Showtime } from "../types";

const day = (iso: string) => new Date(iso).toLocaleDateString("vi-VN", { weekday: "long", day: "2-digit", month: "2-digit" });
const hm = (iso: string) => new Date(iso).toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });

export default function MovieDetail() {
  const { id } = useParams();
  const [movie, setMovie] = useState<Movie | null>(null);
  const [showtimes, setShowtimes] = useState<Showtime[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api<Movie>(`/movies/${id}`), api<Showtime[]>(`/movies/${id}/showtimes`)])
      .then(([m, s]) => { setMovie(m); setShowtimes(s); })
      .catch((e) => setError(e.message));
  }, [id]);

  const byDay = useMemo(() => {
    const g = new Map<string, Showtime[]>();
    showtimes.forEach((s) => { const k = day(s.start_time); g.set(k, [...(g.get(k) ?? []), s]); });
    return [...g.entries()];
  }, [showtimes]);

  if (error) return <p className="error" role="alert">{error}</p>;
  if (!movie) return <p className="muted">Đang tải…</p>;

  return (
    <>
      <div className="detail">
        <PosterArt movie={movie} />
        <div>
          <h1>{movie.title}</h1>
          <div className="facts">
            <span className="tag">{movie.type === "movie" ? "Phim" : "Sự kiện"}</span>
            <span>{movie.duration_min} phút</span>
            <span className={`badge ${movie.status}`}>{STATUS_LABEL[movie.status]}</span>
          </div>
          <p className="lead">{movie.description || "Chưa có mô tả."}</p>
        </div>
      </div>

      <h2>Suất chiếu còn mở bán</h2>
      {byDay.length === 0 && <div className="empty">Hiện chưa có suất chiếu nào cho {movie.type === "movie" ? "phim" : "sự kiện"} này.</div>}
      {byDay.map(([d, list]) => (
        <section key={d} aria-label={d}>
          <h3 className="day">{d}</h3>
          {list.map((s) => (
            <div key={s.id} className="slot">
              <div>
                <div className="slot-time">{hm(s.start_time)} – {hm(s.end_time)}</div>
                <div className="slot-room">{s.room_name}</div>
              </div>
              <div className="slot-price">từ {vnd(s.base_price)}</div>
              <Link className="btn" to={`/showtimes/${s.id}/seats`}>Chọn ghế</Link>
            </div>
          ))}
        </section>
      ))}
    </>
  );
}
