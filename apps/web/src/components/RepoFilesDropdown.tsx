// apps/web/src/components/RepoFilesDropdown.tsx
"use client";

import * as React from "react";
import { CheckCircle2, Circle, ChevronDown, FolderOpen } from "lucide-react";

type Repo = { id: number; full_name: string; default_branch?: string };
type FileStatus = { path: string; status: "indexed" | "not-indexed" };
type Counts = { total: number; indexed: number };

type RepoFilesResponse = {
  repo: {
    github_id: number;
    owner: string;
    name: string;
    default_branch: string;
  };
  files: FileStatus[];
};

export function RepoFilesDropdown({
  repo,
  label = "Files",
  defaultOpen = false,
  counts: countsProp,
  files: filesProp,
}: {
  repo: Repo;
  label?: string;
  defaultOpen?: boolean;
  counts?: Counts | null; // controlled from parent
  files?: FileStatus[] | null; // controlled from parent
}) {
  const [open, setOpen] = React.useState(defaultOpen);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [counts, setCounts] = React.useState<Counts | null>(countsProp ?? null);
  const [files, setFiles] = React.useState<FileStatus[] | null>(
    filesProp ?? null
  );
  const [q, setQ] = React.useState("");

  // keep in sync with parent updates
  React.useEffect(() => {
    if (countsProp) setCounts(countsProp);
  }, [countsProp]);
  React.useEffect(() => {
    if (filesProp) setFiles(filesProp);
  }, [filesProp]);

  const fileCount = counts?.total ?? files?.length ?? 0;
  const indexedDone =
    counts?.indexed ??
    files?.reduce((n, f) => n + (f.status === "indexed" ? 1 : 0), 0) ??
    0;

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`/api/github/files?repoId=${repo.id}`, {
        cache: "no-store",
      });
      if (!r.ok) throw new Error(`${r.status}`);
      const data: RepoFilesResponse = await r.json();
      setFiles(data.files);
      if (!countsProp) {
        const nIdx = data.files.reduce(
          (n, f) => n + (f.status === "indexed" ? 1 : 0),
          0
        );
        setCounts({ total: data.files.length, indexed: nIdx });
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "error";
      setError(`Failed to load files (${message})`);
    } finally {
      setLoading(false);
    }
  }

  React.useEffect(() => {
    if (open && files == null && !loading) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const filtered = React.useMemo(() => {
    if (!files) return [];
    const s = q.trim().toLowerCase();
    return s ? files.filter((f) => f.path.toLowerCase().includes(s)) : files;
  }, [files, q]);

  return (
    <div className="rounded-xl border">
      {/* Toggle header */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between px-3 py-2 text-left"
      >
        <div className="flex items-center gap-2">
          <FolderOpen className="h-4 w-4" />
          <span className="font-medium">{label}</span>
          <span className="text-xs text-muted-foreground">
            {indexedDone}/{fileCount} indexed
          </span>
        </div>
        <ChevronDown
          className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      {/* Panel */}
      {open && (
        <div className="border-t p-3 space-y-3">
          <input
            placeholder="Filter files…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            className="w-full rounded-md border px-2 py-1 text-sm"
          />

          {loading && (
            <div className="text-sm text-muted-foreground">Loading files…</div>
          )}
          {error && <div className="text-sm text-red-600">{error}</div>}

          {!loading && files && (
            <ul className="max-h-80 overflow-auto space-y-1 pr-1">
              {filtered.map((f) => (
                <li key={f.path} className="flex items-center gap-2 text-sm">
                  {f.status === "indexed" ? (
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                  ) : (
                    <Circle className="h-4 w-4 text-gray-400" />
                  )}
                  <span
                    className={
                      f.status === "indexed"
                        ? "truncate"
                        : "truncate text-muted-foreground"
                    }
                    title={f.path}
                  >
                    {f.path}
                  </span>
                </li>
              ))}
              {filtered.length === 0 && (
                <li className="text-sm text-muted-foreground">
                  No files match.
                </li>
              )}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
