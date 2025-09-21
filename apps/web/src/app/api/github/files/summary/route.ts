import { NextRequest } from "next/server";
import { cookies } from "next/headers";

export async function GET(req: NextRequest) {
  const repoId = req.nextUrl.searchParams.get("repoId");
  if (!repoId)
    return new Response(JSON.stringify({ error: "repoId required" }), {
      status: 400,
    });

  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  const brain = process.env.NEXT_PUBLIC_BRAIN_URL!;

  const r = await fetch(`${brain}/repos/${repoId}/files/summary`, {
    headers: { ...(session ? { Authorization: `Bearer ${session}` } : {}) },
    cache: "no-store",
  });

  return new Response(await r.text(), {
    status: r.status,
    headers: { "Content-Type": "application/json" },
  });
}
