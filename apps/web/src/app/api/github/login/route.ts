import { NextResponse } from "next/server";
import crypto from "node:crypto";

export async function GET() {
  const state = crypto.randomBytes(16).toString("hex");
  const redirect = process.env.NEXT_PUBLIC_GITHUB_REDIRECT!;
  const clientId = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID!;
  const url = new URL("https://github.com/login/oauth/authorize");
  url.searchParams.set("client_id", clientId);
  url.searchParams.set("redirect_uri", redirect);
  url.searchParams.set("scope", "repo read:user"); // v1: read repos
  url.searchParams.set("state", state);

  const res = NextResponse.redirect(url.toString(), { status: 302 });
  res.cookies.set("gh_oauth_state", state, {
    httpOnly: true,
    secure: false,
    path: "/",
    maxAge: 600,
  });
  return res;
}
