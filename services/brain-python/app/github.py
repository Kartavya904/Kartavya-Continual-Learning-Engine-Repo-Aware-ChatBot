from __future__ import annotations

import os
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import GithubAccount, User, enc, dec, get_db
from .auth import _decode  # reuse your existing JWT decode

router = APIRouter(prefix="/github", tags=["github"])

GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API = "https://api.github.com"

# Minimal user dependency that matches your auth style
def current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    payload = _decode(authorization.split(" ", 1)[1])
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=404, detail="user not found")
    return user

@router.post("/oauth/exchange")
async def github_oauth_exchange(
    payload: dict,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    code = payload.get("code")
    redirect_uri = payload.get("redirect_uri")
    if not code or not redirect_uri:
        raise HTTPException(status_code=400, detail="code and redirect_uri required")

    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="GitHub OAuth not configured")

    async with httpx.AsyncClient(headers={"Accept": "application/json"}) as client:
        r = await client.post(GITHUB_TOKEN_URL, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        })
        r.raise_for_status()
        tok = r.json().get("access_token")
        if not tok:
            raise HTTPException(status_code=400, detail="Failed to obtain access_token")

        u = await client.get(f"{GITHUB_API}/user", headers={"Authorization": f"Bearer {tok}"})
        u.raise_for_status()
        j: dict[str, Any] = u.json()

    acct = db.scalar(select(GithubAccount).where(GithubAccount.user_id == user.id))
    if not acct:
        acct = GithubAccount(user_id=user.id)
    acct.gh_user_id = int(j["id"])
    acct.login = j["login"]
    acct.name = j.get("name")
    acct.avatar_url = j.get("avatar_url")
    acct.access_token_enc = enc(tok)
    db.add(acct)
    db.commit()
    return {"login": acct.login, "name": acct.name, "avatar_url": acct.avatar_url}

@router.get("/me")
def github_me(user: User = Depends(current_user), db: Session = Depends(get_db)):
    acct = db.scalar(select(GithubAccount).where(GithubAccount.user_id == user.id))
    if not acct:
        raise HTTPException(status_code=404, detail="Not connected")
    return {"login": acct.login, "name": acct.name, "avatar_url": acct.avatar_url}

@router.get("/repos")
async def github_repos(user: User = Depends(current_user), db: Session = Depends(get_db)):
    acct = db.scalar(select(GithubAccount).where(GithubAccount.user_id == user.id))
    if not acct:
        raise HTTPException(status_code=404, detail="Not connected")
    tok = dec(acct.access_token_enc)
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{GITHUB_API}/user/repos",
            params={"per_page": 100, "sort": "updated"},
            headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"},
        )
        r.raise_for_status()
        repos = r.json()

    return [
        {
            "id": x["id"],
            "full_name": x["full_name"],
            "private": x["private"],
            "visibility": x.get("visibility") or ("private" if x["private"] else "public"),
            "default_branch": x["default_branch"],
            "updated_at": x["updated_at"],
            "html_url": x["html_url"],
            "owner_login": x["owner"]["login"],
        }
        for x in repos
    ]
