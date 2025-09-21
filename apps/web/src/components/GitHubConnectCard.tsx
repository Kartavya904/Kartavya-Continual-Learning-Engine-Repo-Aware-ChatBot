"use client";
import { useEffect, useState } from "react";

type Repo = {
  id: number;
  full_name: string;
  private: boolean;
  visibility: string;
  default_branch: string;
  updated_at: string;
  html_url: string;
  owner_login: string;
};

export default function GitHubConnectCard() {
  const [status, setStatus] = useState<
    "idle" | "loading" | "connected" | "error"
  >("idle");
  const [repos, setRepos] = useState<Repo[] | null>(null);

  async function connect() {
    window.location.href = "/api/github/login";
  }

  async function loadRepos() {
    setStatus("loading");
    const r = await fetch("/api/github/repos", { cache: "no-store" });
    if (!r.ok) {
      setStatus("error");
      return;
    }
    const data = await r.json();
    setRepos(data);
    setStatus("connected");
  }

  useEffect(() => {
    // Try to load repos on mount; if 404, user not connected.
    loadRepos().catch(() => setStatus("idle"));
  }, []);

  return (
    <div className="rounded-2xl p-4 border shadow-sm">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">GitHub Connection</h3>
          <p className="text-sm text-muted-foreground">
            Connect your GitHub to list repositories and kick off indexing.
          </p>
        </div>
        {status !== "connected" ? (
          <button
            onClick={connect}
            className="px-3 py-2 rounded-xl border text-sm"
          >
            Connect GitHub
          </button>
        ) : null}
      </div>

      {status === "loading" && (
        <p className="mt-4 text-sm">Loading your repositories…</p>
      )}
      {status === "error" && (
        <p className="mt-4 text-sm text-red-600">
          Couldn’t load repos. Try reconnecting.
        </p>
      )}

      {repos && (
        <div className="mt-4 grid gap-2">
          {repos.map((r) => (
            <div
              key={r.id}
              className="rounded-xl border p-3 flex items-center justify-between"
            >
              <div>
                <div className="font-medium">{r.full_name}</div>
                <div className="text-xs text-muted-foreground">
                  {r.visibility} · branch {r.default_branch} · updated{" "}
                  {new Date(r.updated_at).toLocaleString()}
                </div>
              </div>
              <div className="flex gap-2">
                <a
                  href={r.html_url}
                  target="_blank"
                  className="text-sm underline"
                >
                  Open
                </a>
                <button className="text-sm px-2 py-1 rounded-lg border">
                  Index now
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
