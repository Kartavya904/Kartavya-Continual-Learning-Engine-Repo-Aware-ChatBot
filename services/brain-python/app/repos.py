# services/brain-python/app/repos.py
from __future__ import annotations

from typing import List, Dict, Set
import os, json, asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from .schemas import RepoFilesResponse, FileStatus, RepoInfo
from .db import get_db, GithubAccount, dec  # token lives in DB; decrypt with dec()
from .github import current_user  # your existing auth dependency

router = APIRouter(prefix="/repos", tags=["repos"])

GITHUB_API = "https://api.github.com"

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

def _get_tree_paths(token: str, owner: str, name: str, default_branch: str) -> List[str]:
    branch = _gh_get(token, f"/repos/{owner}/{name}/branches/{default_branch}")
    head_sha = branch["commit"]["sha"]
    tree = _gh_get(token, f"/repos/{owner}/{name}/git/trees/{head_sha}?recursive=1")
    return sorted([e["path"] for e in tree.get("tree", []) if e.get("type") == "blob"])

def _get_user_github_token(db: Session, user_id: int) -> str | None:
    acct = db.query(GithubAccount).filter_by(user_id=user_id).first()
    return dec(acct.access_token_enc) if acct else None  # decrypt from DB

def _indexed_paths(db: Session, owner: str, name: str) -> Set[str]:
    rows = db.execute(
        text("""
          SELECT f.path
          FROM files f
          JOIN repos r ON r.id = f.repo_id
          WHERE r.owner = :owner AND r.name = :name
            AND EXISTS (SELECT 1 FROM chunks c WHERE c.file_id = f.id)
        """),
        {"owner": owner, "name": name},
    ).all()
    return {row[0] for row in rows}

@router.get("/{github_repo_id}/files", response_model=RepoFilesResponse)
def list_repo_files(
    github_repo_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),   # <-- sync Session (matches your db.py)
    user=Depends(current_user),
):
    token = _get_user_github_token(db, user.id)
    if not token:
        raise HTTPException(status_code=401, detail="GitHub account not connected")

    try:
        info = _get_repo_info_by_id(token, github_repo_id)
        paths = _get_tree_paths(token, info["owner"], info["name"], info["default_branch"])
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"GitHub error: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"GitHub error: {e}")

    indexed = _indexed_paths(db, info["owner"], info["name"])
    files = [FileStatus(path=p, status=("indexed" if p in indexed else "not-indexed")) for p in paths]

    return RepoFilesResponse(repo=RepoInfo(**info), files=files)

@router.post("/{github_repo_id}/index")
def index_repo_now(
    github_repo_id: int,
    limit: int = Query(50, ge=1, le=500),            # cap to keep it snappy
    db: Session = Depends(get_db),
    user = Depends(current_user),
):
    """
    DEV stub: index up to `limit` not-yet-indexed files by seeding one random chunk each.
    Uses the existing /dev/embed-random endpoint internally.
    """
    token = _get_user_github_token(db, user.id)
    if not token:
        raise HTTPException(status_code=401, detail="GitHub account not connected")

    # repo + tree
    info = _get_repo_info_by_id(token, github_repo_id)
    paths = _get_tree_paths(token, info["owner"], info["name"], info["default_branch"])
    indexed = _indexed_paths(db, info["owner"], info["name"])

    # choose targets: only not-indexed
    to_index = [p for p in paths if p not in indexed][:limit]
    if not to_index:
        return {
            "repo": info,
            "indexed_now": 0,
            "already_indexed": len(indexed),
            "total_files": len(paths),
            "message": "Nothing to do",
        }

    # self-call brain's dev seeder (simple + robust for now)
    base = os.getenv("SELF_BASE_URL", "http://localhost:8000")
    ok = 0; fail = 0
    with httpx.Client(timeout=30) as client:
        for p in to_index:
            try:
                client.post(
                    f"{base}/dev/embed-random",
                    params={"owner": info["owner"], "name": info["name"], "path": p, "n": 1},
                )
                ok += 1
            except Exception:
                fail += 1

    return {
        "repo": info,
        "indexed_now": ok,
        "failed": fail,
        "already_indexed": len(indexed),
        "total_files": len(paths),
    }

@router.get("/{github_repo_id}/index/stream")
async def index_repo_stream(
    github_repo_id: int,
    limit: int = 50,
    db: Session = Depends(get_db),
    user = Depends(current_user),
):
    """
    DEV: Stream progress as we 'index' up to `limit` not-indexed files by seeding one random chunk each.
    Emits SSE events: 'start', 'file', 'done'.
    """
    token = _get_user_github_token(db, user.id)
    if not token:
        raise HTTPException(status_code=401, detail="GitHub account not connected")

    info = _get_repo_info_by_id(token, github_repo_id)
    paths = _get_tree_paths(token, info["owner"], info["name"], info["default_branch"])
    indexed = _indexed_paths(db, info["owner"], info["name"])
    to_index = [p for p in paths if p not in indexed][:limit]

    base = os.getenv("SELF_BASE_URL", "http://localhost:8000")

    async def eventgen():
        # Tell client we're starting
        start = {"total": len(paths), "already_indexed": len(indexed), "will_index": len(to_index)}
        yield f"event:start\ndata:{json.dumps(start)}\n\n"

        ok = 0
        fail = 0
        async with httpx.AsyncClient(timeout=30) as client:
            for p in to_index:
                try:
                    await client.post(
                        f"{base}/dev/embed-random",
                        params={"owner": info["owner"], "name": info["name"], "path": p, "n": 1},
                    )
                    ok += 1
                    # Tell client one file is done
                    yield f"event:file\ndata:{json.dumps({'path': p, 'ok': True})}\n\n"
                except Exception as e:
                    fail += 1
                    yield f"event:file\ndata:{json.dumps({'path': p, 'ok': False, 'error': str(e)})}\n\n"
                # Give the loop a chance to flush
                await asyncio.sleep(0)

        done = {"indexed_now": ok, "failed": fail}
        yield f"event:done\ndata:{json.dumps(done)}\n\n"

    headers = {
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(eventgen(), media_type="text/event-stream", headers=headers)

@router.get("/{github_repo_id}/files/summary")
def files_summary(
    github_repo_id: int,
    db: Session = Depends(get_db),
    user = Depends(current_user),
):
    token = _get_user_github_token(db, user.id)
    if not token:
        raise HTTPException(status_code=401, detail="GitHub account not connected")
    info = _get_repo_info_by_id(token, github_repo_id)
    paths = _get_tree_paths(token, info["owner"], info["name"], info["default_branch"])
    indexed = _indexed_paths(db, info["owner"], info["name"])
    paths_set = set(paths)
    indexed_count = len(indexed & paths_set) if isinstance(indexed, set) else len([p for p in indexed if p in paths_set])
    return {
        "repo": info,
        "counts": {"total": len(paths), "indexed": indexed_count}
    }
