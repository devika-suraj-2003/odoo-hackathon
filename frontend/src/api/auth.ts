import api from "./client";
import type { User } from "../context/AuthContext";

export async function loginRequest(email: string, password: string): Promise<{ token: string; user: User }> {
  const { data } = await api.post("/auth/login", { email, password });
  const token = data.access_token ?? data.token;
  if (!token) throw new Error("Login response had no token");

  let raw = data.user;
  if (!raw) {
    const me = await api.get("/auth/me", { headers: { Authorization: `Bearer ${token}` } });
    raw = me.data;
  }

  const role = String(raw.role ?? "customer").split(".").pop()!.toLowerCase() as User["role"];
  const user: User = { id: raw.id, name: raw.name ?? raw.full_name ?? raw.email, email: raw.email, role };
  return { token, user };
}