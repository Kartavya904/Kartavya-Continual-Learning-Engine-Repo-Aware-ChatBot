import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function GET(req: NextRequest) {
  const repoId = req.nextUrl.searchParams.get("repoId");
  if (!repoId) {
    return NextResponse.json({ error: "repoId required" }, { status: 400 });
  }

  // Next 15: cookies() is async
  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;

  const brain = process.env.NEXT_PUBLIC_BRAIN_URL!;
  const res = await fetch(`${brain}/repos/${repoId}/files`, {
    headers: {
      "Content-Type": "application/json",
      ...(session ? { Authorization: `Bearer ${session}` } : {}),
    },
    cache: "no-store",
  });

  return new NextResponse(await res.text(), {
    status: res.status,
    headers: { "Content-Type": "application/json" },
  });
}
