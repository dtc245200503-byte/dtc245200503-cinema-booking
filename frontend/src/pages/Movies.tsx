import { useEffect, useState } from "react";
import { api } from "../api";
import MovieCard from "../components/MovieCard";
import type { Movie } from "../types";

const FILTERS = [["", "Tất cả"], ["movie", "Phim"], ["event", "Sự kiện"]] as const;

export default function Movies() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [type, setType] = useState("");
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    setLoaded(false);
    api<Movie[]>(`/movies${type ? `?type=${type}` : ""}`)
      .then((m) => { setMovies(m); setError(""); })
      .catch((e) => setError(e.message))
      .finally(() => setLoaded(true));
  }, [type]);

  return (
    <>
      <section className="hero">
        <div className="wrap">
          <h1>Chọn suất chiếu, chọn ghế, giữ chỗ trong 10 phút</h1>
          <p>Đặt vé xem phim và sự kiện trực tuyến. Hủy sớm để được hoàn tiền theo chính sách của rạp.</p>
          <div className="chips" role="group" aria-label="Lọc theo loại">
            {FILTERS.map(([v, label]) => (
              <button key={v} className="chip" aria-pressed={type === v} onClick={() => setType(v)}>{label}</button>
            ))}
          </div>
        </div>
      </section>

      <div className="wrap page">
        {error && <p className="error" role="alert">{error}</p>}
        {!error && loaded && movies.length === 0 && (
          <div className="empty">Chưa có phim hoặc sự kiện nào trong mục này.</div>
        )}
        <div className="poster-grid">
          {movies.map((m) => <MovieCard key={m.id} movie={m} />)}
        </div>
      </div>
    </>
  );
}
