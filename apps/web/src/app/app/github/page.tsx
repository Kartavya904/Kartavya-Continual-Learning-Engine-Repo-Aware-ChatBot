"use client";
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

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

export default function GitHubLabPage() {
  const [loading, setLoading] = useState(true);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [q, setQ] = useState("");
  const [vis, setVis] = useState<"all" | "public" | "private">("all");
  const [sort, setSort] = useState<"updated" | "name">("updated");

  useEffect(() => {
    (async () => {
      setLoading(true);
      const r = await fetch("/api/github/repos", { cache: "no-store" });
      if (r.ok) setRepos(await r.json());
      setLoading(false);
    })();
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
    if (sort === "name") {
      list = [...list].sort((a, b) => a.full_name.localeCompare(b.full_name));
    } else {
      list = [...list].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
    }
    return list;
  }, [repos, q, vis, sort]);

  return (
    <div className="container mx-auto max-w-5xl py-8 space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">GitHub Lab</h1>
        <p className="text-sm text-muted-foreground">
          Browse your repositories and kick off indexing.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search repositories…"
          className="h-9 w-64 rounded-lg border px-3 text-sm"
        />
        <select
          value={vis}
          onChange={(e) =>
            setVis(e.target.value as "all" | "public" | "private")
          }
          className="h-9 rounded-lg border px-2 text-sm"
        >
          <option value="all">All</option>
          <option value="public">Public</option>
          <option value="private">Private</option>
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as "updated" | "name")}
          className="h-9 rounded-lg border px-2 text-sm"
        >
          <option value="updated">Recently updated</option>
          <option value="name">Name (A→Z)</option>
        </select>
      </div>

      <div className="grid gap-2">
        {loading ? (
          Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="h-16 rounded-xl border bg-gray-50 animate-pulse"
            />
          ))
        ) : filtered.length === 0 ? (
          <div className="rounded-xl border p-6 text-sm text-muted-foreground">
            No repositories match your filters.
          </div>
        ) : (
          filtered.map((r) => (
            <div
              key={r.id}
              className="rounded-xl border p-3 flex items-center justify-between hover:bg-gray-50"
            >
              <div>
                <div className="font-medium">{r.full_name}</div>
                <div className="text-xs text-muted-foreground">
                  {r.visibility} · branch {r.default_branch} · updated{" "}
                  {new Date(r.updated_at).toLocaleString()}
                </div>
              </div>
              <div className="flex gap-2">
                <Link
                  href={r.html_url}
                  target="_blank"
                  className="text-sm underline"
                >
                  Open
                </Link>
                <button className="text-sm px-2 py-1 rounded-lg border">
                  Index now
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
