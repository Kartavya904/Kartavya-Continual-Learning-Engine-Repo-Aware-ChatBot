import { NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function GET() {
  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value; // adjust if your cookie key differs
  const r = await fetch(`${process.env.NEXT_PUBLIC_BRAIN_URL}/github/repos`, {
    headers: session ? { Authorization: `Bearer ${session}` } : {},
    cache: "no-store",
  });
  const data = await r.json().catch(() => ({}));
  return NextResponse.json(data, { status: r.status });
}
