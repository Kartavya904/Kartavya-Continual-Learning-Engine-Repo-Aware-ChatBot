# app/repos.py
from __future__ import annotations

import os
import json
import base64
import hashlib
import asyncio
import httpx
import importlib
import codecs
from typing import List, Dict, Set, Tuple, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .schemas import RepoFilesResponse, FileStatus, RepoInfo
from .db import get_db, GithubAccount, dec, engine, insert_chunk_with_vec, EMBED_DIM
from .github import current_user

router = APIRouter(prefix="/repos", tags=["repos"])

GITHUB_API = "https://api.github.com"
MAX_BLOB_BYTES = int(os.getenv("MAX_INDEX_BLOB_BYTES", str(512 * 1024)))  # 512 KB
SKIP_EXTS = {
    x.strip().lower()
    for x in os.getenv(
        "SKIP_FILE_EXTS",
        # Skip common binaries + large/low-value assets by default
        ".png,.jpg,.jpeg,.gif,.pdf,.zip,.tar,.gz,.7z,.exe,.dll,.so,.dylib,.bin,.ico,.svg",
    ).split(",")
}


# --- GitHub helpers --------------------------------------------------------


def _gh_get(token: str, url: str) -> Dict:
    if not url.startswith("http"):
        url = f"{GITHUB_API}{url}"
    r = httpx.get(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        timeout=20.0,
    )
    r.raise_for_status()
    return r.json()


def _get_repo_info_by_id(token: str, repo_id: int) -> Dict:
    data = _gh_get(token, f"/repositories/{repo_id}")
    owner, name = data["full_name"].split("/", 1)
    return {
        "github_id": data["id"],
        "owner": owner,
        "name": name,
        "default_branch": data["default_branch"],
    }


def _resolve_branch_and_head(
    token: str, owner: str, name: str, default_branch: str
) -> Tuple[str, str]:
    """Returns (branch_name, head_sha). Falls back if default branch 404s."""
    try:
        branch = _gh_get(token, f"/repos/{owner}/{name}/branches/{default_branch}")
        return branch["name"], branch["commit"]["sha"]
    except httpx.HTTPStatusError as e:
        if e.response.status_code != 404:
            raise
        branches = _gh_get(token, f"/repos/{owner}/{name}/branches")
        if not branches:
            raise HTTPException(status_code=404, detail="No branches found in repo")
        branch = branches[0]
        return branch["name"], branch["commit"]["sha"]


def _get_tree_entries(
    token: str, owner: str, name: str, head_sha: str
) -> List[Dict]:
    tree = _gh_get(token, f"/repos/{owner}/{name}/git/trees/{head_sha}?recursive=1")
    entries = []
    for e in tree.get("tree", []):
        if e.get("type") == "blob":
            entries.append({"path": e["path"], "sha": e["sha"], "size": e.get("size")})
    return sorted(entries, key=lambda x: x["path"])


def _get_blob_text(
    token: str, owner: str, name: str, blob_sha: str, size: Optional[int]
) -> Optional[str]:
    """
    Fetch a blob and return UTF-8/UTF-16 text, or None if binary/too large.
    Robust to GitHub’s newline-broken base64.
    """
    if size and int(size) > MAX_BLOB_BYTES:
        return None

    data = _gh_get(token, f"/repos/{owner}/{name}/git/blobs/{blob_sha}")
    if data.get("encoding") != "base64":
        return None

    content_b64 = (data.get("content") or "").encode("utf-8")
    try:
        raw = base64.b64decode(content_b64, validate=False)  # allow newlines/whitespace
    except Exception:
        raw = base64.b64decode(b"".join(content_b64.split()))

    if len(raw) > MAX_BLOB_BYTES:
        return None

    # Try common encodings
    try:
        return raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        pass

    # UTF-8 BOM
    if raw.startswith(codecs.BOM_UTF8):
        try:
            return raw.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError:
            pass

    # UTF-16 (BOM or heuristic)
    if raw.startswith(codecs.BOM_UTF16_LE) or raw.startswith(codecs.BOM_UTF16_BE):
        try:
            return raw.decode("utf-16", errors="strict")
        except UnicodeDecodeError:
            pass
    if raw.count(b"\x00") > max(1, len(raw) // 50):
        try:
            return raw.decode("utf-16", errors="strict")
        except UnicodeDecodeError:
            return None

    return None


def _indexed_paths(db: Session, owner: str, name: str) -> Set[str]:
    rows = db.execute(
        text(
            """
          SELECT f.path
          FROM files f
          JOIN repos r ON r.id = f.repo_id
          WHERE r.owner = :owner AND r.name = :name
            AND EXISTS (SELECT 1 FROM chunks c WHERE c.file_id = f.id)
        """
        ),
        {"owner": owner, "name": name},
    ).all()
    return {row[0] for row in rows}


def _get_user_github_token(db: Session, user_id: int) -> str | None:
    acct = db.query(GithubAccount).filter_by(user_id=user_id).first()
    return dec(acct.access_token_enc) if acct else None


def _load_indexer():
    """
    Try both 'app.indexer' and 'indexer' import styles so this works
    in dev and inside the Docker image. Returns (chunk_code, embed_texts).
    """
    try:
        idx = importlib.import_module(".indexer", package=__package__)
    except Exception:
        idx = importlib.import_module("indexer")
    return getattr(idx, "chunk_code"), getattr(idx, "embed_texts")


# --- Public endpoints ------------------------------------------------------


@router.get("/{github_repo_id}/files", response_model=RepoFilesResponse)
def list_repo_files(
    github_repo_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    token = _get_user_github_token(db, user.id)
    if not token:
        raise HTTPException(status_code=401, detail="GitHub account not connected")
    info = _get_repo_info_by_id(token, github_repo_id)
    branch_name, head_sha = _resolve_branch_and_head(
        token, info["owner"], info["name"], info["default_branch"]
    )
    entries = _get_tree_entries(token, info["owner"], info["name"], head_sha)
    indexed = _indexed_paths(db, info["owner"], info["name"])
    files = [
        FileStatus(
            path=e["path"],
            status=("indexed" if e["path"] in indexed else "not-indexed"),
        )
        for e in entries
    ]
    info_out = {
        "github_id": info["github_id"],
        "owner": info["owner"],
        "name": info["name"],
        "default_branch": branch_name,
    }
    return RepoFilesResponse(repo=RepoInfo(**info_out), files=files)


@router.get("/{github_repo_id}/files/summary")
def files_summary(
    github_repo_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    token = _get_user_github_token(db, user.id)
    if not token:
        raise HTTPException(status_code=401, detail="GitHub account not connected")
    info = _get_repo_info_by_id(token, github_repo_id)
    try:
        branch_name, head_sha = _resolve_branch_and_head(
            token, info["owner"], info["name"], info["default_branch"]
        )
        entries = _get_tree_entries(token, info["owner"], info["name"], head_sha)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {"repo": info, "counts": {"total": 0, "indexed": 0}}
        raise
    indexed = _indexed_paths(db, info["owner"], info["name"])
    total = len(entries)
    indexed_count = sum(1 for e in entries if e["path"] in indexed)
    return {"repo": info, "counts": {"total": total, "indexed": indexed_count}}


# --- Streaming real indexing (writes to DB) --------------------------------


@router.get("/{github_repo_id}/index/stream")
async def index_repo_stream(
    github_repo_id: int,
    limit: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Streams real-time indexing progress via Server-Sent Events (SSE) and WRITES to DB.
    Events:
      - start            {repo, branch, head, counts}
      - file-start       {path, size_hint}
      - file-skip        {path, reason}
      - file-chunked     {path, chunks, total_lines, total_chars}
      - file-embedded    {path, embed_count}
      - file-written     {path, chunks_written}
      - progress         {considered, files_written, chunks_written, errors}
      - done             {summary}
      - error            {message}
    """
    token = _get_user_github_token(db, user.id)
    if not token:
        raise HTTPException(status_code=401, detail="GitHub account not connected")

    info = _get_repo_info_by_id(token, github_repo_id)
    branch_name, head_sha = _resolve_branch_and_head(
        token, info["owner"], info["name"], info["default_branch"]
    )
    entries = _get_tree_entries(token, info["owner"], info["name"], head_sha)
    indexed = _indexed_paths(db, info["owner"], info["name"])

    def is_skipped(path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in SKIP_EXTS

    candidates = [
        e for e in entries if e["path"] not in indexed and not is_skipped(e["path"])
    ]
    to_index = candidates[:limit]

    chunk_code, embed_texts = _load_indexer()

    async def eventgen():
        # Initial: announce plan
        start_payload = {
            "repo": {
                "github_id": info["github_id"],
                "owner": info["owner"],
                "name": info["name"],
            },
            "branch": branch_name,
            "head": head_sha,
            "counts": {
                "total_candidates": len(entries),
                "already_indexed": len(indexed),
                "will_index": len(to_index),
                "limit": limit,
            },
        }
        yield f"event:start\ndata:{json.dumps(start_payload)}\n\n"

        files_written = 0
        chunks_written = 0
        errors = 0
        considered = 0

        for e in to_index:
            path = e["path"]
            size_hint = int(e.get("size") or 0)
            considered += 1
            # file-start
            yield f"event:file-start\ndata:{json.dumps({'path': path, 'size_hint': size_hint})}\n\n"

            try:
                blob = _get_blob_text(
                    token, info["owner"], info["name"], e["sha"], e.get("size")
                )
                if not blob:
                    yield f"event:file-skip\ndata:{json.dumps({'path': path, 'reason': 'binary-or-large'})}\n\n"
                    # progress
                    yield f"event:progress\ndata:{json.dumps({'considered': considered, 'files_written': files_written, 'chunks_written': chunks_written, 'errors': errors})}\n\n"
                    await asyncio.sleep(0)
                    continue

                # Chunk
                chunks = chunk_code(blob) or []
                if not chunks:
                    yield f"event:file-skip\ndata:{json.dumps({'path': path, 'reason': 'no-chunks'})}\n\n"
                    yield f"event:progress\ndata:{json.dumps({'considered': considered, 'files_written': files_written, 'chunks_written': chunks_written, 'errors': errors})}\n\n"
                    await asyncio.sleep(0)
                    continue

                total_lines = blob.count("\n") + 1
                total_chars = len(blob)
                yield f"event:file-chunked\ndata:{json.dumps({'path': path, 'chunks': len(chunks), 'total_lines': total_lines, 'total_chars': total_chars})}\n\n"

                # Embed
                texts = [c["text"] for c in chunks]
                vecs = embed_texts(texts)
                if len(vecs) != len(chunks):
                    raise RuntimeError(
                        f"embed_texts returned {len(vecs)} vecs for {len(chunks)} chunks"
                    )
                yield f"event:file-embedded\ndata:{json.dumps({'path': path, 'embed_count': len(vecs)})}\n\n"

                # Write all chunks
                wrote_any = False
                for ch, vec in zip(chunks, vecs):
                    if len(vec) != EMBED_DIM:
                        raise RuntimeError(
                            f"bad embed dim={len(vec)} expected={EMBED_DIM}"
                        )
                    insert_chunk_with_vec(
                        owner=info["owner"],
                        name=info["name"],
                        path=path,
                        start_line=ch["start_line"],
                        end_line=ch["end_line"],
                        embedding=vec,
                    )
                    wrote_any = True
                    chunks_written += 1
                    # Give UI a heartbeat during large files
                    if chunks_written % 50 == 0:
                        yield f"event:progress\ndata:{json.dumps({'considered': considered, 'files_written': files_written, 'chunks_written': chunks_written, 'errors': errors})}\n\n"
                        await asyncio.sleep(0)

                if wrote_any:
                    files_written += 1
                    # best-effort per-file metadata update
                    try:
                        h = hashlib.sha1(
                            blob.encode("utf-8", errors="ignore")
                        ).hexdigest()
                        with engine.begin() as conn:
                            conn.execute(
                                text(
                                    """
                                UPDATE files f SET commit = :commit, content_hash = :h
                                FROM repos r
                                WHERE f.repo_id = r.id
                                  AND r.owner = :owner AND r.name = :name
                                  AND f.path = :path
                            """
                                ),
                                {
                                    "commit": head_sha,
                                    "h": h,
                                    "owner": info["owner"],
                                    "name": info["name"],
                                    "path": path,
                                },
                            )
                    except Exception:
                        # Ignore metadata update errors in stream mode
                        pass

                yield f"event:file-written\ndata:{json.dumps({'path': path, 'chunks_written': len(chunks)})}\n\n"

            except Exception as ex:
                errors += 1
                yield f"event:error\ndata:{json.dumps({'path': path, 'message': str(ex)})}\n\n"

            # progress after each file
            yield f"event:progress\ndata:{json.dumps({'considered': considered, 'files_written': files_written, 'chunks_written': chunks_written, 'errors': errors})}\n\n"
            await asyncio.sleep(0)

        summary = {
            "repo": {
                "github_id": info["github_id"],
                "owner": info["owner"],
                "name": info["name"],
            },
            "branch": branch_name,
            "head": head_sha,
            "counts": {
                "considered": len(to_index),
                "files_written": files_written,
                "chunks_written": chunks_written,
                "errors": errors,
            },
        }
        yield f"event:done\ndata:{json.dumps(summary)}\n\n"

    headers = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    return StreamingResponse(eventgen(), media_type="text/event-stream", headers=headers)


# --- Non-stream fallback: batch indexing (writes to DB, returns JSON) ------


@router.post("/{github_repo_id}/index")
def index_repo_write(
    github_repo_id: int,
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    REAL INDEXING (non-stream). Fetches, chunks, embeds, and WRITES to Postgres.
    Uses insert_chunk_with_vec(), which validates vector size == EMBED_DIM.
    """
    token = _get_user_github_token(db, user.id)
    if not token:
        raise HTTPException(status_code=401, detail="GitHub account not connected")

    info = _get_repo_info_by_id(token, github_repo_id)
    branch_name, head_sha = _resolve_branch_and_head(
        token, info["owner"], info["name"], info["default_branch"]
    )
    entries = _get_tree_entries(token, info["owner"], info["name"], head_sha)
    indexed = _indexed_paths(db, info["owner"], info["name"])

    def is_skipped(path: str) -> bool:
        ext = os.path.splitext(path)[1].lower()
        return ext in SKIP_EXTS

    candidates = [
        e for e in entries if e["path"] not in indexed and not is_skipped(e["path"])
    ]
    to_index = candidates[:limit]

    chunk_code, embed_texts = _load_indexer()

    files_written = 0
    chunks_written = 0
    errors = 0
    results = []

    for e in to_index:
        path = e["path"]
        size_hint = int(e.get("size") or 0)
        try:
            blob = _get_blob_text(
                token, info["owner"], info["name"], e["sha"], e.get("size")
            )
            if not blob:
                results.append(
                    {"path": path, "ok": True, "skipped": "binary-or-large"}
                )
                continue

            chunks = chunk_code(blob) or []
            if not chunks:
                results.append({"path": path, "ok": True, "skipped": "no-chunks"})
                continue

            texts = [c["text"] for c in chunks]
            vecs = embed_texts(texts)
            if len(vecs) != len(chunks):
                raise RuntimeError(
                    f"embed_texts returned {len(vecs)} vecs for {len(chunks)} chunks"
                )

            wrote_any = False
            for ch, vec in zip(chunks, vecs):
                if len(vec) != EMBED_DIM:
                    raise RuntimeError(
                        f"bad embed dim={len(vec)} expected={EMBED_DIM}"
                    )
                insert_chunk_with_vec(
                    owner=info["owner"],
                    name=info["name"],
                    path=path,
                    start_line=ch["start_line"],
                    end_line=ch["end_line"],
                    embedding=vec,
                )
                wrote_any = True
                chunks_written += 1

            if wrote_any:
                files_written += 1
                try:
                    h = hashlib.sha1(
                        blob.encode("utf-8", errors="ignore")
                    ).hexdigest()
                    with engine.begin() as conn:
                        conn.execute(
                            text(
                                """
                                UPDATE files f SET commit = :commit, content_hash = :h
                                FROM repos r
                                WHERE f.repo_id = r.id
                                  AND r.owner = :owner AND r.name = :name
                                  AND f.path = :path
                            """
                            ),
                            {
                                "commit": head_sha,
                                "h": h,
                                "owner": info["owner"],
                                "name": info["name"],
                                "path": path,
                            },
                        )
                except Exception:
                    pass

            results.append(
                {"path": path, "ok": True, "chunks": len(chunks), "size_hint": size_hint}
            )

        except Exception as ex:
            errors += 1
            results.append({"path": path, "ok": False, "error": str(ex)})

    summary = {
        "repo": {**info, "default_branch": branch_name, "head": head_sha},
        "counts": {
            "considered": len(to_index),
            "files_written": files_written,
            "chunks_written": chunks_written,
            "errors": errors,
        },
        "results": results,
    }
    return summary


# --- Dangerous: drop all chunks for a repo --------------------------------


@router.delete("/{github_repo_id}/index")
def delete_repo_index(
    github_repo_id: int,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    """
    Delete ALL chunks for this GitHub repo. Keeps repo/file rows,
    but resets files.commit/content_hash so UI shows 0 indexed.
    """
    token = _get_user_github_token(db, user.id)
    if not token:
        raise HTTPException(status_code=401, detail="GitHub account not connected")

    info = _get_repo_info_by_id(token, github_repo_id)  # gives owner/name
    params = {"owner": info["owner"], "name": info["name"]}

    del_chunks = db.execute(
        text(
            """
      DELETE FROM chunks c
      USING files f, repos r
      WHERE c.file_id = f.id
        AND f.repo_id = r.id
        AND r.owner = :owner
        AND r.name  = :name
    """
        ),
        params,
    ).rowcount

    db.execute(
        text(
            """
      UPDATE files f
      SET commit = NULL, content_hash = NULL
      FROM repos r
      WHERE f.repo_id = r.id
        AND r.owner = :owner
        AND r.name  = :name
    """
        ),
        params,
    )

    db.commit()
    return {"deleted_chunks": del_chunks, "repo": info}
