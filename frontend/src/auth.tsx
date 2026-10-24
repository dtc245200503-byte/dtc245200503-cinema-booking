import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { api, setToken } from "./api";
import type { TokenOut, User } from "./types";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>(null!);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<User>("/auth/me").then(setUser).catch(() => setToken(null)).finally(() => setLoading(false));
  }, []);

  const accept = (t: TokenOut) => { setToken(t.access_token); setUser(t.user); };

  return (
    <Ctx.Provider value={{
      user, loading,
      login: async (email, password) => accept(await api<TokenOut>("/auth/login", { body: { email, password } })),
      register: async (email, password, full_name) =>
        accept(await api<TokenOut>("/auth/register", { body: { email, password, full_name } })),
      logout: () => { setToken(null); setUser(null); },
    }}>
      {children}
    </Ctx.Provider>
  );
}
