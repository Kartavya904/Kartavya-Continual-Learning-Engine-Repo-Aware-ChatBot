"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { RepoFilesDropdown } from "@/components/RepoFilesDropdown";

type Repo = {
  id: number;
  full_name: string; // "owner/name"
  private: boolean;
  visibility: string; // "public" | "private"
  default_branch: string;
  updated_at: string; // ISO
  html_url: string;
  owner_login: string;
};

export default function GitHubConnectCard() {
  const [status, setStatus] = useState<
    "idle" | "loading" | "connected" | "error"
  >("idle");
  const [repos, setRepos] = useState<Repo[]>([]);
  const [q, setQ] = useState("");
  const [vis, setVis] = useState<"all" | "public" | "private">("all");
  const [sort, setSort] = useState<"updated" | "name">("updated");

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
    setRepos(await r.json());
    setStatus("connected");
  }

  useEffect(() => {
    // If user is connected, this will succeed; otherwise we stay idle and show the connect button
    loadRepos().catch(() => setStatus("idle"));
  }, []);

  const filtered = useMemo(() => {
    let list = repos;
    if (q) {
      const s = q.toLowerCase();
      list = list.filter((r) => r.full_name.toLowerCase().includes(s));
    }
    if (vis !== "all") {
      list = list.filter((r) => (vis === "private" ? r.private : !r.private));
    }
    list = [...list].sort((a, b) =>
      sort === "name"
        ? a.full_name.localeCompare(b.full_name)
        : b.updated_at.localeCompare(a.updated_at)
    );
    return list;
  }, [repos, q, vis, sort]);

  return (
    <div className="rounded-2xl border shadow-sm p-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">GitHub Connection</h3>
          <p className="text-sm text-muted-foreground">
            Connect your GitHub to list repositories and kick off indexing.
          </p>
        </div>
        {status !== "connected" && (
          <button
            onClick={connect}
            className="px-3 py-2 rounded-xl border text-sm hover:bg-accent"
          >
            Connect GitHub
          </button>
        )}
      </div>

      {/* Loading/Error/Controls */}
      {status === "loading" && (
        <p className="mt-4 text-sm">Loading your repositories…</p>
      )}
      {status === "error" && (
        <p className="mt-4 text-sm text-red-600">
          Couldn’t load repos. Try reconnecting.
        </p>
      )}

      {status === "connected" && (
        <>
          {/* Controls */}
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search repositories…"
              className="h-9 w-64 rounded-lg border px-3 text-sm"
            />
            <select
              value={vis}
              onChange={(e) => setVis(e.target.value as typeof vis)}
              className="h-9 rounded-lg border px-2 text-sm"
            >
              <option value="all">All</option>
              <option value="public">Public</option>
              <option value="private">Private</option>
            </select>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as typeof sort)}
              className="h-9 rounded-lg border px-2 text-sm"
            >
              <option value="updated">Recently updated</option>
              <option value="name">Name (A→Z)</option>
            </select>
          </div>

          {/* Repo list */}
          <div className="mt-3 grid gap-2">
            {filtered.length === 0 ? (
              <div className="rounded-xl border p-6 text-sm text-muted-foreground">
                No repositories match your filters.
              </div>
            ) : (
              filtered.map((r) => (
                <article
                  key={r.id}
                  className="rounded-xl border p-3 hover:bg-muted/40"
                >
                  {/* Card header row */}
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="font-medium truncate">{r.full_name}</div>
                      <div className="text-xs text-muted-foreground">
                        {r.visibility} · branch {r.default_branch} · updated{" "}
                        {new Date(r.updated_at).toLocaleString()}
                      </div>
                    </div>
                    <div className="flex shrink-0 gap-2">
                      <Link
                        href={r.html_url}
                        target="_blank"
                        className="text-sm underline"
                      >
                        Open
                      </Link>
                      <button className="text-sm px-2 py-1 rounded-lg border hover:bg-accent">
                        Index now
                      </button>
                    </div>
                  </div>

                  {/* Dropdown lives on its own row; no duplicate repo name */}
                  <div className="mt-2">
                    <RepoFilesDropdown repo={r} label="Files" />
                  </div>
                </article>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
