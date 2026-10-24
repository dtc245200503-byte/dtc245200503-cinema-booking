import { ReactNode } from "react";

/** Khung chuẩn cho mọi trang: rộng tối đa 1120px, căn giữa, nội dung căn trái. */
export default function Page({ children }: { children: ReactNode }) {
  return <div className="wrap page">{children}</div>;
}
