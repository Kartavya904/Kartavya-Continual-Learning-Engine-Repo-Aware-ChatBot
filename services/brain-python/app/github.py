# services/brain-python/app/github.py
from __future__ import annotations
import os, hmac, hashlib, logging
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from .auth import _decode  # reuse JWT decode from auth.py

router = APIRouter(prefix="/github", tags=["github"])

class InstallStartReq(BaseModel):
    next: str | None = None

class InstallStartRes(BaseModel):
    url: str
    next: str | None = None

class MeRes(BaseModel):
    connected: bool
    username: str | None = None

def _require_user_id(authorization: str | None) -> int:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing token")
    payload = _decode(authorization.split(" ", 1)[1])
    return int(payload["sub"])

@router.get("/me", response_model=MeRes)
def github_me(authorization: str | None = Header(default=None)):
    _require_user_id(authorization)
    # TODO: check DB once we store GitHub linkage
    return MeRes(connected=False, username=None)

@router.post("/install", response_model=InstallStartRes)
def github_install_start(body: InstallStartReq, authorization: str | None = Header(default=None)):
    _require_user_id(authorization)
    slug = os.getenv("GITHUB_APP_SLUG")  # e.g., "my-cool-app"
    if slug:
        url = f"https://github.com/apps/{slug}/installations/new"
    else:
        web_origin = os.getenv("WEB_ORIGIN", "http://localhost:3000")
        url = f"{web_origin}/github/placeholder"
    return InstallStartRes(url=url, next=body.next)

def _verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    if not secret:
        return True  # allow through in dev when not configured
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    received = signature_header.split("=", 1)[1]
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, received)

@router.post("/webhook")
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
):
    body = await request.body()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    if not _verify_signature(secret, body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="invalid signature")
    logging.getLogger("github.webhook").info(
        "event=%s delivery=%s bytes=%d", x_github_event, x_github_delivery, len(body)
    )
    # TODO: parse event JSON and enqueue indexing later
    return {"ok": True}
