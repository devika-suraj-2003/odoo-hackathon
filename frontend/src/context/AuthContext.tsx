import { createContext, useContext, useState, type ReactNode } from "react";

export type Role = "admin" | "staff" | "customer";
export interface User { id?: number; name: string; email: string; role: Role; }

interface AuthCtx {
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthCtx>(null as any);

export const homeFor = (role: Role) =>
  role === "customer" ? "/portal/subscriptions" : "/dashboard";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    try { const u = localStorage.getItem("user"); return u ? JSON.parse(u) : null; }
    catch { return null; }
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("token"));

  const login = (t: string, u: User) => {
    localStorage.setItem("token", t);
    localStorage.setItem("user", JSON.stringify(u));
    setToken(t);
    setUser(u);
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);