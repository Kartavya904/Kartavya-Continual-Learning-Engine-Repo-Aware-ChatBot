import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get("session")?.value;
  const res = await fetch(`${process.env.NEXT_PUBLIC_BRAIN_URL}/github/me`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    cache: "no-store",
  });
  const json = await res.json();
  return NextResponse.json(json);
}
