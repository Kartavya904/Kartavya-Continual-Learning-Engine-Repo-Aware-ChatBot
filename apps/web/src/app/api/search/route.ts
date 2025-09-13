// Dev proxy: text -> toy embedding (hash-BoW 1536d) -> brain /search
type JSONish = Record<string, unknown>;

function textToVec(
  text: string,
  dim = Number(process.env.NEXT_PUBLIC_EMBED_DIM ?? 1536)
): number[] {
  const vec = new Float32Array(dim);
  const toks = text.toLowerCase().split(/\W+/).filter(Boolean);
  for (const t of toks) {
    // FNV-1a style hash per token
    let h = 2166136261 >>> 0;
    for (let i = 0; i < t.length; i++) {
      h ^= t.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    const idx = (h >>> 0) % dim;
    vec[idx] += 1;
  }
  // L2 normalize
  let n = 0;
  for (let i = 0; i < dim; i++) n += vec[i] * vec[i];
  n = Math.sqrt(n) || 1;
  const out = Array(dim);
  for (let i = 0; i < dim; i++) out[i] = vec[i] / n;
  return out;
}

export async function POST(req: Request) {
  const base = process.env.NEXT_PUBLIC_BRAIN_URL!;
  const inBody = (await req.json().catch(() => ({}))) as JSONish;
  const text = String(inBody.q ?? inBody.query ?? inBody.text ?? "").trim();
  const top_k = Number(inBody.k ?? inBody.top_k ?? 5) || 5;
  if (!text)
    return Response.json({ error: "missing query text" }, { status: 400 });

  // 1) Local dev embed
  const vector = textToVec(text);

  // 2) Call brain /search with the vector
  const r = await fetch(`${base}/search`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query: vector, top_k }),
  });

  const ct = r.headers.get("content-type") || "";
  const raw = await r.text(); // read once
  let json: Record<string, unknown>;
  try {
    json = ct.includes("application/json") ? JSON.parse(raw) : { raw };
  } catch {
    json = { raw };
  }

  return new Response(JSON.stringify(json), {
    status: r.status,
    headers: { "content-type": "application/json" },
  });
}
