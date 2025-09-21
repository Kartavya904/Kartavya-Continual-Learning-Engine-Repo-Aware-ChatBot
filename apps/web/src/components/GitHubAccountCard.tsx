"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { RepoFilesDropdown } from "@/components/RepoFilesDropdown";

type GhMe = { login: string; name?: string; avatar_url?: string };

export default function GitHubAccountCard() {
  const [loading, setLoading] = useState(true);
  const [me, setMe] = useState<GhMe | null>(null);

  useEffect(() => {
    (async () => {
      setLoading(true);
      const r = await fetch("/api/github/status", { cache: "no-store" });
      if (r.ok) setMe(await r.json());
      setLoading(false);
    })();
  }, []);

  if (loading) {
    return (
      <div className="rounded-2xl border p-4">
        <div className="h-5 w-40 bg-gray-100 rounded animate-pulse" />
        <div className="mt-2 h-4 w-64 bg-gray-100 rounded animate-pulse" />
      </div>
    );
  }

  const connected = !!me;

  return (
    <div className="rounded-2xl border p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="font-semibold">GitHub</div>
          {connected ? (
            <span className="text-xs rounded-full border px-2 py-0.5">
              Connected
            </span>
          ) : (
            <span className="text-xs rounded-full border px-2 py-0.5">
              Not connected
            </span>
          )}
        </div>
        {!connected ? (
          <a
            href="/api/github/login"
            className="px-3 py-1.5 rounded-lg border text-sm"
          >
            Connect
          </a>
        ) : (
          <Link
            href="/app/github"
            className="px-3 py-1.5 rounded-lg border text-sm"
          >
            Open GitHub Lab
          </Link>
        )}
      </div>

      {connected ? (
        <div className="mt-4 flex items-center gap-3">
          <img
            src={
              me!.avatar_url ?? "https://avatars.githubusercontent.com/u/0?v=4"
            }
            alt="avatar"
            className="h-10 w-10 rounded-full border"
          />
          <div>
            <div className="font-medium">{me!.name ?? me!.login}</div>
            <div className="text-sm text-muted-foreground">@{me!.login}</div>
          </div>
        </div>
      ) : (
        <p className="mt-3 text-sm text-muted-foreground">
          Connect your GitHub account to enable indexing and the GitHub Lab.
        </p>
      )}
    </div>
  );
}
