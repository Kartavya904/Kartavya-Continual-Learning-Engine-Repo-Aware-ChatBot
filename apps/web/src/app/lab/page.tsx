"use client";

import { useState } from "react";

type Hit = {
  file_path?: string;
  path?: string;
  start_line?: number;
  end_line?: number;
  commit?: string;
  score?: number;
  dist?: number;
  preview?: string;
};

type Payload = {
  hits?: unknown[];
  results?: unknown[];
  took_ms?: number;
  error?: string;
  [k: string]: unknown;
};

function normalizeHits(data: Payload): Hit[] {
  const arr = (data?.hits ?? data?.results ?? []) as Record<string, unknown>[];
  return arr.map((r) => ({
    file_path:
      typeof r.file_path === "string"
        ? r.file_path
        : typeof r.path === "string"
        ? r.path
        : typeof r.file === "string"
        ? r.file
        : typeof r.source === "string"
        ? r.source
        : undefined,
    path:
      typeof r.path === "string"
        ? r.path
        : typeof r.file_path === "string"
        ? r.file_path
        : undefined,
    start_line:
      typeof r.start_line === "number"
        ? r.start_line
        : typeof r.start === "number"
        ? r.start
        : typeof r.line_start === "number"
        ? r.line_start
        : undefined,
    end_line:
      typeof r.end_line === "number"
        ? r.end_line
        : typeof r.end === "number"
        ? r.end
        : typeof r.line_end === "number"
        ? r.line_end
        : undefined,
    commit: typeof r.commit === "string" ? r.commit : undefined,
    score: typeof r.score === "number" ? r.score : undefined,
    dist: typeof r.dist === "number" ? r.dist : undefined,
    preview:
      typeof r.preview === "string"
        ? r.preview
        : typeof r.snippet === "string"
        ? r.snippet
        : typeof r.chunk === "string"
        ? r.chunk
        : undefined,
  }));
}

export default function LabPage() {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [hits, setHits] = useState<Hit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [took, setTook] = useState<number | undefined>(undefined);

  async function run() {
    if (!q || busy) return;
    setBusy(true);
    setError(null);
    setTook(undefined);
    try {
      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ q, k: 5 }),
      });

      // Read the body ONCE, then decode
      const ct = res.headers.get("content-type") || "";
      const raw = await res.text();
      let payload: Payload;
      try {
        payload = ct.includes("application/json")
          ? (JSON.parse(raw) as Payload)
          : ({ raw } as Payload);
      } catch {
        payload = { raw } as Payload;
      }

      if (!res.ok) {
        throw new Error(`${res.status}: ${JSON.stringify(payload)}`);
      }

      setHits(normalizeHits(payload));
      if (typeof payload.took_ms === "number") setTook(payload.took_ms);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Search failed");
      setHits([]);
    } finally {
      setBusy(false);
    }
  }

  async function copy(line: string) {
    try {
      await navigator.clipboard.writeText(line);
    } catch {
      /* noop */
    }
  }

  return (
    <main className="mx-auto max-w-3xl p-8 space-y-6">
      <h1 className="text-2xl font-semibold">Lab: Text → KNN Results</h1>

      <div className="flex items-center gap-2">
        <input
          className="flex-1 border rounded px-3 py-2"
          placeholder="Ask about the repo… e.g., indexing"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
        />
        <button
          className="border rounded px-4 py-2 bg-black text-white disabled:opacity-50"
          onClick={run}
          disabled={!q || busy}
        >
          {busy ? "Searching…" : "Search"}
        </button>
        {typeof took === "number" && (
          <span className="text-xs text-gray-500">
            took {Math.round(took)} ms
          </span>
        )}
      </div>

      {error && <p className="text-red-600 text-sm break-all">{error}</p>}

      <section className="space-y-3">
        {hits.length > 0 ? (
          hits.map((h, i) => {
            const file = h.file_path ?? h.path ?? "(unknown path)";
            const loc = h.start_line ? `${file}:${h.start_line}` : file;
            return (
              <div key={i} className="border rounded p-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-mono text-sm truncate">{loc}</div>
                  <div className="flex items-center gap-3 text-xs text-gray-500">
                    {typeof h.dist === "number" && (
                      <span>dist {h.dist.toFixed(3)}</span>
                    )}
                    {typeof h.score === "number" && (
                      <span>score {h.score.toFixed(3)}</span>
                    )}
                    <button
                      className="border rounded px-2 py-1"
                      onClick={() => copy(loc)}
                      title="Copy path:line"
                    >
                      Copy
                    </button>
                  </div>
                </div>
                {h.preview && (
                  <pre className="mt-2 overflow-x-auto whitespace-pre-wrap text-xs bg-gray-50 p-2 rounded">
                    {h.preview}
                  </pre>
                )}
              </div>
            );
          })
        ) : (
          <p className="text-gray-500 text-sm">No results yet.</p>
        )}
      </section>
    </main>
  );
}
