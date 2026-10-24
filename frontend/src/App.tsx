import { ReactNode } from "react";
import { Link, Navigate, NavLink, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import Page from "./components/Page";
import Admin from "./pages/Admin";
import AuthPage from "./pages/AuthPage";
import Checkout from "./pages/Checkout";
import MovieDetail from "./pages/MovieDetail";
import Movies from "./pages/Movies";
import MyBookings from "./pages/MyBookings";
import SeatPicker from "./pages/SeatPicker";

function Guard({ children, admin = false }: { children: ReactNode; admin?: boolean }) {
  const { user, loading } = useAuth();
  if (loading) return <Page><p className="muted">Đang tải…</p></Page>;
  if (!user) return <Navigate to="/login" replace />;
  if (admin && user.role !== "admin") return <Navigate to="/" replace />;
  return <Page>{children}</Page>;
}

export default function App() {
  const { user, logout } = useAuth();
  return (
    <div className="shell">
      <header className="topbar">
        <div className="wrap bar">
          <Link to="/" className="brand">Rạp &amp; Sự kiện</Link>
          <nav className="nav" aria-label="Điều hướng chính">
            <NavLink to="/" end>Phim và sự kiện</NavLink>
            {user && <NavLink to="/my-bookings">Vé của tôi</NavLink>}
            {user?.role === "admin" && <NavLink to="/admin">Quản trị</NavLink>}
            {user ? (
              <>
                <span className="who">{user.full_name}</span>
                <button className="link" onClick={logout}>Đăng xuất</button>
              </>
            ) : (
              <NavLink to="/login">Đăng nhập</NavLink>
            )}
          </nav>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Movies />} />
          <Route path="/login" element={<Page><AuthPage /></Page>} />
          <Route path="/movies/:id" element={<Page><MovieDetail /></Page>} />
          <Route path="/showtimes/:id/seats" element={<Guard><SeatPicker /></Guard>} />
          <Route path="/checkout/:id" element={<Guard><Checkout /></Guard>} />
          <Route path="/my-bookings" element={<Guard><MyBookings /></Guard>} />
          <Route path="/admin" element={<Guard admin><Admin /></Guard>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="footer"><div className="wrap">Hệ thống đặt vé xem phim và sự kiện</div></footer>
    </div>
  );
}
