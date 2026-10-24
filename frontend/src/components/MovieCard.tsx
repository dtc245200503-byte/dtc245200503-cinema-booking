import { Link } from "react-router-dom";
import { STATUS_LABEL } from "../api";
import type { Movie } from "../types";
import PosterArt from "./PosterArt";

export default function MovieCard({ movie }: { movie: Movie }) {
  return (
    <Link to={`/movies/${movie.id}`} className="movie">
      <div className="movie-art"><PosterArt movie={movie} /></div>
      <div className="movie-body">
        <h3 className="movie-title">{movie.title}</h3>
        <div className="movie-meta">
          <span className="tag">{movie.type === "movie" ? "Phim" : "Sự kiện"}</span>
          <span>{movie.duration_min} phút</span>
          {movie.status !== "showing" && <span className={`badge ${movie.status}`}>{STATUS_LABEL[movie.status]}</span>}
        </div>
      </div>
    </Link>
  );
}
