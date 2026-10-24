const BASE = import.meta.env.VITE_API_BASE ?? "/api";

let token: string | null = localStorage.getItem("token");

export function setToken(t: string | null) {
  token = t;
  if (t) localStorage.setItem("token", t);
  else localStorage.removeItem("token");
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function parse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = `Lỗi ${res.status}`;
    if (res.status === 429) msg = "Bạn thao tác quá nhanh, vui lòng thử lại sau ít phút";
    try {
      const data = await res.json();
      if (typeof data.detail === "string") msg = data.detail;
      else if (Array.isArray(data.detail)) msg = "Dữ liệu nhập chưa hợp lệ, vui lòng kiểm tra lại";
    } catch { /* giữ thông báo mặc định */ }
    throw new ApiError(res.status, msg);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

const authHeader = (): Record<string, string> => (token ? { Authorization: `Bearer ${token}` } : {});

export async function api<T>(path: string, opts: { method?: string; body?: unknown } = {}): Promise<T> {
  const res = await fetch(BASE + path, {
    method: opts.method ?? (opts.body ? "POST" : "GET"),
    headers: { ...(opts.body ? { "Content-Type": "application/json" } : {}), ...authHeader() },
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  return parse<T>(res);
}

/** Tải file lên (multipart). Không tự đặt Content-Type để trình duyệt thêm boundary. */
export async function upload<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(BASE + path, { method: "POST", headers: authHeader(), body: form });
  return parse<T>(res);
}

export const vnd = (n: number) => n.toLocaleString("vi-VN") + " ₫";
export const fmtTime = (iso: string) =>
  new Date(iso).toLocaleString("vi-VN", { dateStyle: "short", timeStyle: "short" });

export const STATUS_LABEL: Record<string, string> = {
  pending_payment: "Chờ thanh toán", paid: "Đã thanh toán", cancelled: "Đã hủy",
  refund_pending: "Chờ hoàn tiền", refunded: "Đã hoàn tiền", expired: "Hết hạn",
  pending: "Chờ duyệt", approved: "Đã duyệt", rejected: "Từ chối",
  success: "Thành công", failed: "Thất bại", open: "Đang mở", showing: "Đang chiếu",
  upcoming: "Sắp chiếu", ended: "Đã kết thúc",
};

export const POSTER_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const POSTER_MAX = 2 * 1024 * 1024;
/** Kiểm tra ảnh poster phía trình duyệt (server vẫn kiểm tra lại). Trả về thông báo lỗi hoặc chuỗi rỗng. */
export function checkPoster(f: File): string {
  if (!POSTER_TYPES.includes(f.type)) return "Chỉ chấp nhận ảnh JPG, PNG hoặc WEBP";
  if (f.size > POSTER_MAX) return "Ảnh quá lớn, tối đa 2 MB";
  return "";
}
