import { cookies } from "next/headers";
import { NextResponse } from "next/server";

export async function POST(req: Request) {
  const cookieStore = await cookies();
  const token = cookieStore.get("session")?.value;
  const body = await req.json().catch(() => ({}));
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_BRAIN_URL}/github/install`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify(body),
    }
  );
  return NextResponse.json(await res.json(), { status: res.status });
}
