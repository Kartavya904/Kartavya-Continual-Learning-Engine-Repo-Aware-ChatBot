import { NextRequest } from "next/server";
import { cookies } from "next/headers";

export async function GET(req: NextRequest) {
  const repoId = req.nextUrl.searchParams.get("repoId");
  const limit = req.nextUrl.searchParams.get("limit") ?? "50";
  if (!repoId) return new Response("repoId required", { status: 400 });

  const cookieStore = await cookies();
  const session = cookieStore.get("session")?.value;
  const brain = process.env.NEXT_PUBLIC_BRAIN_URL!;

  const res = await fetch(
    `${brain}/repos/${repoId}/index/stream?limit=${limit}`,
    {
      headers: {
        ...(session ? { Authorization: `Bearer ${session}` } : {}),
        Accept: "text/event-stream",
      },
    }
  );

  if (!res.body) return new Response("No body", { status: 502 });

  return new Response(res.body, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
