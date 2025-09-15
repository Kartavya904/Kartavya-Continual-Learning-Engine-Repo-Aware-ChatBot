import { cookies } from "next/headers";
import { SESSION_COOKIE } from "@/lib/auth";
export async function POST() {
  (await cookies()).set(SESSION_COOKIE, "", { path: "/", maxAge: 0 });
  return Response.json({ ok: true });
}
