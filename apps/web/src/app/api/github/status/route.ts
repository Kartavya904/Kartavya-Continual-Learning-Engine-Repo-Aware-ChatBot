// apps/web/src/app/api/github/status/route.ts
import { NextResponse } from "next/server";

// Stub: replace with real call to brain `/github/me` later.
export async function GET() {
  return NextResponse.json({ connected: false });
}
