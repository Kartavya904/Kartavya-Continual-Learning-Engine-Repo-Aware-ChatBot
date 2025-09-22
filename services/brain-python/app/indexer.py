from __future__ import annotations

import os
import hashlib
import traceback
from typing import List, Dict

# Single-source-of-truth: use LOCAL only.
# Ensure your .env sets EMBED_DIM and LOCAL_EMBED_MODEL appropriately.
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))
LOCAL_EMBED_MODEL = os.getenv("LOCAL_EMBED_MODEL", "BAAI/bge-small-en-v1.5")

_fast_model = None  # lazy loaded fastembed model instance


def _load_local_model():
    """
    Lazy-load the local model (fastembed.TextEmbedding).
    Prints verbose model load information.
    """
    global _fast_model
    if _fast_model is not None:
        return _fast_model

    try:
        print(f"[EMBED-LOCAL] Loading local embed model `{LOCAL_EMBED_MODEL}` (expected dim={EMBED_DIM}) ...")
        # lazy import so module only required when embedding is used
        from fastembed import TextEmbedding

        _fast_model = TextEmbedding(model_name=LOCAL_EMBED_MODEL)
        print(f"[EMBED-LOCAL] Model loaded: {LOCAL_EMBED_MODEL}")
    except Exception as e:
        print("[EMBED-LOCAL-ERR] Failed to load local model:", e)
        print(traceback.format_exc())
        raise
    return _fast_model


def chunk_code(text: str, max_chars: int | None = None, overlap: int | None = None) -> List[Dict]:
    """
    Chunk text into overlapping chunks for embedding.
    Returns list of dicts: {"text": str, "start_line": int, "end_line": int}
    """
    max_chars = int(os.getenv("CHUNK_MAX_CHARS", str(max_chars or 2000)))
    overlap = int(os.getenv("CHUNK_OVERLAP_CHARS", str(overlap or 200)))

    lines = text.splitlines(keepends=True)
    if not lines:
        return []

    chunks = []
    # Build chunks by accumulating lines until max_chars reached.
    cur_lines = []
    cur_chars = 0
    start_line = 0

    for i, ln in enumerate(lines):
        ln_len = len(ln)
        if cur_chars + ln_len > max_chars and cur_chars > 0:
            # flush chunk
            chunk_text = "".join(cur_lines)
            chunks.append(
                {
                    "text": chunk_text,
                    "start_line": start_line + 1,
                    "end_line": i,
                }
            )
            # prepare overlap: keep last 'overlap' chars worth of tail
            tail = ""
            tail_chars = 0
            # greedily keep trailing lines until we hit overlap
            for rev_ln in reversed(cur_lines):
                if tail_chars + len(rev_ln) > overlap:
                    break
                tail = rev_ln + tail
                tail_chars += len(rev_ln)
            cur_lines = [tail] if tail else []
            cur_chars = len(tail)
            start_line = i
        cur_lines.append(ln)
        cur_chars += ln_len

    # flush remaining
    if cur_lines:
        chunk_text = "".join(cur_lines)
        chunks.append({"text": chunk_text, "start_line": start_line + 1, "end_line": len(lines)})

    # Debug info
    print(f"[CHUNK] input_len_chars={len(text)} lines={len(lines)} chunks={len(chunks)} max_chars={max_chars} overlap={overlap}")
    for idx, c in enumerate(chunks, start=1):
        preview = c["text"][:200].replace("\n", "\\n")
        print(f"[CHUNK] #{idx:02d} lines={c['start_line']}..{c['end_line']} chars={len(c['text'])} preview={preview!r}")

    return chunks


def _embed_local(texts: List[str]) -> List[List[float]]:
    """
    Embed using local fastembed model only. Very verbose printing.
    Returns list of vectors (list of floats).
    """
    if not texts:
        return []

    try:
        model = _load_local_model()
        print(f"[EMBED-LOCAL] Embedding {len(texts)} texts (showing preview + vector shape).")
        # print preview for each text
        for i, t in enumerate(texts, start=1):
            preview = t[:300].replace("\n", "\\n")
            print(f"[EMBED-LOCAL] Text #{i:03d} len={len(t)} preview={preview!r}")

        # fastembed returns an iterator/sequence of numpy arrays; convert to python floats
        raw_vecs = list(model.embed(texts))
        vecs: List[List[float]] = [list(map(float, v)) for v in raw_vecs]

        # sanity checks and verbose print
        for i, v in enumerate(vecs, start=1):
            if v is None:
                print(f"[EMBED-LOCAL-ERR] #{i} got None vector")
                continue
            # print shape + first few dims
            dim = len(v)
            print(f"[EMBED-LOCAL] #{i:03d} vector_dim={dim} first12={[round(x,6) for x in v[:12]]} ...")
            if dim != EMBED_DIM:
                print(f"[EMBED-LOCAL-WARN] vector_dim {dim} != EMBED_DIM {EMBED_DIM}")

        return vecs
    except Exception as e:
        print("[EMBED-LOCAL-ERR] exception during local embedding:", e)
        print(traceback.format_exc())
        raise


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Public wrapper. Uses only local embedding.
    """
    return _embed_local(texts)


# Small helper so you can do a basic smoke test if you run indexer.py directly.
if __name__ == "__main__":
    sample = "def hello():\n    print('hello world')\n" * 20
    print("=== indexer.py self-test ===")
    ch = chunk_code(sample, max_chars=200, overlap=50)
    texts = [c["text"] for c in ch]
    vecs = embed_texts(texts)
    print(f"Self-test: chunks={len(ch)} vectors={len(vecs)}")
    for i, v in enumerate(vecs, start=1):
        print(f"  vec#{i} dim={len(v)} sample_first8={[round(x,6) for x in (v[:8] if v else [])]}")