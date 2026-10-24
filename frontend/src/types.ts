// Kiểu dữ liệu khớp với schema của backend.
// Có thể sinh tự động: npm run gen:types (backend đang chạy ở cổng 8000).
export type Role = "customer" | "admin";
export interface User { id: number; email: string; full_name: string; phone: string | null; role: Role }
export interface TokenOut { access_token: string; token_type: string; user: User }

export interface Movie {
  id: number; title: string; type: "movie" | "event"; description: string | null;
  duration_min: number; poster_url: string | null; status: "showing" | "upcoming" | "ended";
}
export interface Showtime {
  id: number; movie_id: number; room_id: number; start_time: string; end_time: string;
  base_price: number; status: "open" | "cancelled"; room_name: string | null; movie_title: string | null;
}
export interface Seat { id: number; row_label: string; seat_number: number; seat_type: "standard" | "vip"; price: number; taken: boolean }
export interface SeatMap { showtime: Showtime; seats: Seat[] }

export type BookingStatus = "pending_payment" | "paid" | "cancelled" | "refund_pending" | "refunded" | "expired";
export interface Refund {
  id: number; booking_id: number; amount: number; percent: number; reason: string | null;
  status: "pending" | "approved" | "rejected"; reject_reason: string | null;
  created_at: string; processed_at: string | null;
}
export interface Booking {
  id: number; status: BookingStatus; total_amount: number; expires_at: string; created_at: string;
  showtime: Showtime; seats: { seat_id: number; label: string; price: number }[];
  refund: Refund | null; customer: string | null;
}
export interface Payment { id: number; booking_id: number; method: string; amount: number; status: string; transaction_code: string; paid_at: string | null }
export interface Room { id: number; name: string; total_rows: number; total_cols: number }
export interface Stats {
  revenue: number; refunded: number; net: number;
  bookings_by_status: Record<string, number>; revenue_by_movie: { title: string; revenue: number }[];
}
export interface AuditLog { id: number; user_id: number | null; action: string; entity_type: string; entity_id: number | null; detail: unknown; created_at: string }
