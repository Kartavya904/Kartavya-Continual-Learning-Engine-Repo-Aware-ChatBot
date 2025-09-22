import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function POST(req: NextRequest) {
  const repoId = req.nextUrl.searchParams.get("repoId");
  const limit = req.nextUrl.searchParams.get("limit") ?? "50";
  if (!repoId)
    return NextResponse.json({ error: "repoId required" }, { status: 400 });

  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;

  const brain = process.env.NEXT_PUBLIC_BRAIN_URL!;
  const res = await fetch(`${brain}/repos/${repoId}/index?limit=${limit}`, {
    method: "POST",
    headers: {
      ...(session ? { Authorization: `Bearer ${session}` } : {}),
      "Content-Type": "application/json",
    },
    cache: "no-store",
  });

  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}

/**
 * DELETE /api/github/index?repoId=123
 * Proxies to Brain: DELETE /repos/:id/index
 */
export async function DELETE(req: NextRequest) {
  const repoId = req.nextUrl.searchParams.get("repoId");
  if (!repoId)
    return NextResponse.json({ error: "repoId required" }, { status: 400 });

  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;

  const brain = process.env.NEXT_PUBLIC_BRAIN_URL!;
  const res = await fetch(`${brain}/repos/${repoId}/index`, {
    method: "DELETE",
    headers: { ...(session ? { Authorization: `Bearer ${session}` } : {}) },
    cache: "no-store",
  });

  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
