// apps/web/src/app/api/github/install/route.ts
import { NextResponse } from "next/server";

// Stub: produce a placeholder target; later, fetch install URL from brain.
export async function POST(req: Request) {
  //   const _body =
  await req.json().catch(() => ({}));
  const url = "/github/placeholder";
  return NextResponse.json({ url });
}

export async function GET() {
  // Optional convenience for manual testing
  return NextResponse.json({ url: "/github/placeholder" });
}
