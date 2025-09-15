import { cookies } from "next/headers";
import { SESSION_COOKIE, SESSION_MAX_AGE } from "@/lib/auth";

export async function POST(req: Request) {
  const body = await req.json();
  const base = process.env.NEXT_PUBLIC_BRAIN_URL!;
  const r = await fetch(`${base}/auth/signup`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) return Response.json(data, { status: r.status });
  // Immediately log in after sign-up
  const r2 = await fetch(`${base}/auth/login`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email: body.email, password: body.password }),
  });
  const d2 = await r2.json();
  if (!r2.ok) return Response.json(d2, { status: r2.status });
  (await cookies()).set(SESSION_COOKIE, d2.token, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: SESSION_MAX_AGE,
    secure: false,
  });
  return Response.json({ user: d2.user }, { status: 200 });
}
