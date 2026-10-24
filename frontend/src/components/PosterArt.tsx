import type { Movie } from "../types";

function hue(s: string) {
  let h = 0;
  for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 360;
  return h;
}
const initials = (t: string) =>
  t.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join("");

/** Ảnh poster tỉ lệ 2:3. Chưa có ảnh thì hiện nền màu riêng theo tên phim kèm chữ cái đầu. */
export default function PosterArt({ movie }: { movie: Pick<Movie, "title" | "poster_url"> }) {
  const h = hue(movie.title);
  const bg = movie.poster_url ? undefined : { background: `linear-gradient(165deg, hsl(${h} 40% 30%), hsl(${(h + 50) % 360} 48% 16%))` };
  return (
    <div className="art" style={bg}>
      {movie.poster_url && <img src={movie.poster_url} alt={`Poster ${movie.title}`} loading="lazy" />}
      {!movie.poster_url && <span className="mono" aria-hidden="true">{initials(movie.title)}</span>}
    </div>
  );
}
