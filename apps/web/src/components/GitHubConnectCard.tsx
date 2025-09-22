"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { RepoFilesDropdown } from "@/components/RepoFilesDropdown";
import { RotateCw, X } from "lucide-react";

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

type FileStatus = { path: string; status: "indexed" | "not-indexed" };
type Counts = { total: number; indexed: number };

type Prefetched = {
  counts?: Counts;
  files?: FileStatus[];
};

const PREFETCH_FILES_FOR = 3;
const GLOBAL_REFRESH_MS = 3 * 180_000;

export default function GitHubConnectCard() {
  const [status, setStatus] = useState<
    "idle" | "loading" | "connected" | "error"
  >("idle");
  const [repos, setRepos] = useState<Repo[]>([]);
  const [q, setQ] = useState("");
  const [vis, setVis] = useState<"all" | "public" | "private">("all");
  const [sort, setSort] = useState<"updated" | "name">("updated");
  const [prefetched, setPrefetched] = useState<Record<number, Prefetched>>({});
  const [indexingRepoId, setIndexingRepoId] = useState<number | null>(null);
  const [deletingRepoId, setDeletingRepoId] = useState<number | null>(null);
  const [globRefreshing, setGlobRefreshing] = useState(false);
  const autoRefresher = useRef<NodeJS.Timeout | null>(null);

  // --- helpers --------------------------------------------------------------

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

    const list: Repo[] = await r.json();
    setRepos(list);
    setStatus("connected");

    // Prefetch summary for ALL repos
    Promise.allSettled(
      list.map((repo) =>
        fetch(`/api/github/files/summary?repoId=${repo.id}`, {
          cache: "no-store",
        })
          .then((res) => (res.ok ? res.json() : null))
          .then((data) => {
            if (!data) return;
            setPrefetched((prev) => ({
              ...prev,
              [repo.id]: {
                ...(prev[repo.id] || {}),
                counts: data.counts as Counts,
              },
            }));
          })
      )
    );

    // Prefetch full files for the first N
    const top = list.slice(0, PREFETCH_FILES_FOR);
    Promise.allSettled(
      top.map((repo) =>
        fetch(`/api/github/files?repoId=${repo.id}`, { cache: "no-store" })
          .then((res) => (res.ok ? res.json() : null))
          .then((data) => {
            if (!data) return;
            const files: FileStatus[] = data.files;
            const nIdx = files.reduce(
              (n, f) => n + (f.status === "indexed" ? 1 : 0),
              0
            );
            setPrefetched((prev) => ({
              ...prev,
              [repo.id]: {
                counts: prev[repo.id]?.counts ?? {
                  total: files.length,
                  indexed: nIdx,
                },
                files,
              },
            }));
          })
      )
    );
  }

  function bumpCounts(repoId: number, deltaIndexed: number) {
    setPrefetched((prev) => {
      const cur = prev[repoId] || {};
      const counts = cur.counts || { total: 0, indexed: 0 };
      const next: Counts = {
        total: counts.total,
        indexed: Math.max(0, counts.indexed + deltaIndexed),
      };
      return { ...prev, [repoId]: { ...cur, counts: next } };
    });
  }

  function markFileIndexed(repoId: number, path: string) {
    setPrefetched((prev) => {
      const cur = prev[repoId] || {};
      if (!cur.files) return prev;
      const files = cur.files.map((f) =>
        f.path === path ? { ...f, status: "indexed" } : f
      );
      return { ...prev, [repoId]: { ...cur, files } };
    });
  }

  // Live SSE index (used by "Index now")
  function handleIndexLive(repoId: number, limit = 50) {
    setIndexingRepoId(repoId);

    const es = new EventSource(
      `/api/github/index/stream?repoId=${repoId}&limit=${limit}`
    );
    es.addEventListener("file", (ev) => {
      try {
        const data = JSON.parse((ev as MessageEvent).data) as {
          path: string;
          ok: boolean;
        };
        if (data.ok) {
          bumpCounts(repoId, 1);
          markFileIndexed(repoId, data.path);
        }
      } catch {}
    });
    es.addEventListener("done", () => {
      es.close();
      setIndexingRepoId(null);
      // reconcile counts/files from server:
      fetch(`/api/github/files?repoId=${repoId}`, { cache: "no-store" })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (!data) return;
          const files: FileStatus[] = data.files;
          const nIdx = files.reduce(
            (n, f) => n + (f.status === "indexed" ? 1 : 0),
            0
          );
          setPrefetched((prev) => ({
            ...prev,
            [repoId]: { counts: { total: files.length, indexed: nIdx }, files },
          }));
        })
        .catch(() => void 0);
    });
    es.onerror = () => {
      es.close();
      setIndexingRepoId(null);
    };
  }

  // NEW: Unindex button handler
  async function handleUnindex(repoId: number) {
    if (indexingRepoId === repoId) return; // safety: disabled in UI
    const ok = window.confirm(
      "Delete all embeddings for this repository?\nYou can reindex from scratch after."
    );
    if (!ok) return;

    setDeletingRepoId(repoId);
    try {
      const r = await fetch(`/api/github/index?repoId=${repoId}`, {
        method: "DELETE",
      });
      if (!r.ok) throw new Error(`delete failed: ${r.status}`);

      // If we know counts, set indexed → 0. Otherwise fetch summary for accurate total.
      setPrefetched((prev) => {
        const cur = prev[repoId] || {};
        const counts = cur.counts
          ? { total: cur.counts.total, indexed: 0 }
          : undefined;
        const files = cur.files
          ? cur.files.map((f) => ({ ...f, status: "not-indexed" as const }))
          : undefined;
        return { ...prev, [repoId]: { counts, files } };
      });

      // If we didn't have counts, fetch them now so header shows total/0
      if (!prefetched[repoId]?.counts) {
        fetch(`/api/github/files/summary?repoId=${repoId}`, {
          cache: "no-store",
        })
          .then((res) => (res.ok ? res.json() : null))
          .then((data) => {
            if (!data) return;
            setPrefetched((prev) => ({
              ...prev,
              [repoId]: {
                ...(prev[repoId] || {}),
                counts: data.counts as Counts,
              },
            }));
          })
          .catch(() => void 0);
      }
    } finally {
      setDeletingRepoId(null);
    }
  }

  // Global refresh
  async function refreshAll() {
    if (globRefreshing) return;
    setGlobRefreshing(true);
    try {
      await Promise.allSettled(
        repos.map((repo) =>
          fetch(`/api/github/files/summary?repoId=${repo.id}`, {
            cache: "no-store",
          })
            .then((res) => (res.ok ? res.json() : null))
            .then((data) => {
              if (!data) return;
              setPrefetched((prev) => ({
                ...prev,
                [repo.id]: {
                  ...(prev[repo.id] || {}),
                  counts: data.counts as Counts,
                },
              }));
            })
        )
      );
    } finally {
      setGlobRefreshing(false);
    }
  }

  useEffect(() => {
    loadRepos().catch(() => setStatus("idle"));
  }, []);

  // Auto-refresh counts every 3 minutes
  useEffect(() => {
    if (status !== "connected") return;
    if (autoRefresher.current) clearInterval(autoRefresher.current);
    autoRefresher.current = setInterval(() => {
      refreshAll().catch(() => void 0);
    }, GLOBAL_REFRESH_MS);
    return () => {
      if (autoRefresher.current) clearInterval(autoRefresher.current);
    };
  }, [status, repos.length]);

  const filtered = useMemo(() => {
    let list = repos;
    if (q) {
      const s = q.toLowerCase();
      list = list.filter((r) => r.full_name.toLowerCase().includes(s));
    }
    if (vis !== "all")
      list = list.filter((r) => (vis === "private" ? r.private : !r.private));
    list = [...list].sort((a, b) =>
      sort === "name"
        ? a.full_name.localeCompare(b.full_name)
        : b.updated_at.localeCompare(a.updated_at)
    );
    return list;
  }, [repos, q, vis, sort]);

  // --- render ---------------------------------------------------------------

  return (
    <div className="rounded-2xl border shadow-sm p-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">GitHub Connection</h3>
          <p className="text-sm text-muted-foreground">
            Connect your GitHub to list repositories and kick off indexing.
          </p>
        </div>
        {status === "connected" ? (
          <button
            onClick={() => refreshAll()}
            disabled={globRefreshing}
            className="px-3 py-2 rounded-xl border text-sm hover:bg-accent disabled:opacity-60 inline-flex items-center gap-2"
            title="Refresh counts (auto every 3 min)"
          >
            <RotateCw
              className={`h-4 w-4 ${globRefreshing ? "animate-spin" : ""}`}
            />
            Refresh
          </button>
        ) : (
          <button
            onClick={connect}
            className="px-3 py-2 rounded-xl border text-sm hover:bg-accent"
          >
            Connect GitHub
          </button>
        )}
      </div>

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
              filtered.map((r) => {
                const counts = prefetched[r.id]?.counts;
                const isIndexing = indexingRepoId === r.id;
                const isDeleting = deletingRepoId === r.id;
                return (
                  <article
                    key={r.id}
                    className="rounded-xl border p-3 hover:bg-muted/40"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-medium truncate">
                          {r.full_name}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {r.visibility} · branch {r.default_branch}
                          {counts && (
                            <>
                              {" "}
                              · {counts.indexed}/{counts.total} indexed
                            </>
                          )}
                          {" · updated "}
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
                        <button
                          onClick={() => handleIndexLive(r.id, 50)}
                          disabled={isIndexing || isDeleting}
                          className="text-sm px-2 py-1 rounded-lg border hover:bg-accent disabled:opacity-60"
                          title="Index (streams live)"
                        >
                          {isIndexing ? "Indexing…" : "Index now"}
                        </button>
                        <button
                          onClick={() => handleUnindex(r.id)}
                          disabled={isIndexing || isDeleting}
                          className="text-sm px-2 py-1 rounded-lg border hover:bg-accent disabled:opacity-60 inline-flex items-center gap-1"
                          title="Delete embeddings (reset)"
                        >
                          <X className="h-4 w-4" />
                          Reset
                        </button>
                      </div>
                    </div>

                    <div className="mt-2">
                      <RepoFilesDropdown
                        repo={r}
                        label="Files"
                        counts={prefetched[r.id]?.counts ?? null}
                        files={prefetched[r.id]?.files ?? null}
                      />
                    </div>
                  </article>
                );
              })
            )}
          </div>
        </>
      )}
    </div>
  );
}
