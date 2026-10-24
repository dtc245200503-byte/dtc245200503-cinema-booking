import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function AuthPage() {
  const { login, register } = useAuth();
  const nav = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", password: "", full_name: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm({ ...form, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(""); setBusy(true);
    try {
      if (mode === "login") await login(form.email, form.password);
      else await register(form.email, form.password, form.full_name);
      nav("/");
    } catch (err) {
      setError((err as Error).message);
    } finally { setBusy(false); }
  }

  return (
    <div className="auth-wrap">
      <div className="panel auth-card">
        <h1>{mode === "login" ? "Đăng nhập" : "Tạo tài khoản"}</h1>
        <form className="stack" onSubmit={submit}>
          {mode === "register" && (
            <label>Họ và tên<input required value={form.full_name} onChange={set("full_name")} autoComplete="name" /></label>
          )}
          <label>Email<input type="email" required value={form.email} onChange={set("email")} autoComplete="email" /></label>
          <label>Mật khẩu
            <input type="password" required minLength={mode === "register" ? 8 : 1} value={form.password}
              onChange={set("password")} autoComplete={mode === "login" ? "current-password" : "new-password"} />
            {mode === "register" && <span className="hint">Tối thiểu 8 ký tự</span>}
          </label>
          {error && <div className="error" role="alert">{error}</div>}
          <button disabled={busy}>{mode === "login" ? "Đăng nhập" : "Đăng ký"}</button>
        </form>
        <p className="auth-switch">
          {mode === "login" ? "Chưa có tài khoản?" : "Đã có tài khoản?"}{" "}
          <button className="link" type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
            {mode === "login" ? "Đăng ký" : "Đăng nhập"}
          </button>
        </p>
      </div>
    </div>
  );
}
