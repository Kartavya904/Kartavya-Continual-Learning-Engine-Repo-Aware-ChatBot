import { cookies } from "next/headers";
import { SESSION_COOKIE } from "@/lib/auth";

export async function GET() {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!token) return Response.json({ error: "unauthorized" }, { status: 401 });
  const base = process.env.NEXT_PUBLIC_BRAIN_URL!;
  const r = await fetch(`${base}/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  const data = await r.json();
  return Response.json(data, { status: r.status });
}
