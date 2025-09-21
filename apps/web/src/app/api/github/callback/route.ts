import { NextRequest, NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const cookieStore = await cookies();
  const cookieState = cookieStore.get("gh_oauth_state")?.value;

  if (!code || !state || !cookieState || state !== cookieState) {
    return NextResponse.redirect(
      new URL("/app/settings?gh=failed", url.origin)
    );
  }

  // Pull your HttpOnly session cookie and forward as Bearer
  const session = cookieStore.get("session")?.value; // adjust name if different
  const r = await fetch(
    `${process.env.NEXT_PUBLIC_BRAIN_URL}/github/oauth/exchange`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(session ? { Authorization: `Bearer ${session}` } : {}),
      },
      body: JSON.stringify({
        code,
        redirect_uri: process.env.NEXT_PUBLIC_GITHUB_REDIRECT,
      }),
      cache: "no-store",
    }
  );

  const dest = new URL(
    `/app/settings?gh=${r.ok ? "connected" : "failed"}`,
    url.origin
  );
  const res = NextResponse.redirect(dest);
  res.cookies.delete("gh_oauth_state");
  return res;
}
