# services/brain-python/app/repos.py
from __future__ import annotations

from typing import List, Dict, Set
import httpx
from fastapi import APIRouter, Depends, HTTPException, Path
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
