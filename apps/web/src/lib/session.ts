// server-only
import { cookies } from "next/headers";

export type User = {
  id: number;
  first_name?: string;
  last_name?: string;
  email?: string;
};

export async function getUserServer(): Promise<User | null> {
  const token = (await cookies()).get("session")?.value;
  if (!token) return null;
  const base = process.env.NEXT_PUBLIC_BRAIN_URL!;
  const r = await fetch(`${base}/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!r.ok) return null;
  return (await r.json()) as User;
}
