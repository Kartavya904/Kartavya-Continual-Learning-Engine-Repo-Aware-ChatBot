from datetime import datetime, timedelta, timezone
import os, jwt
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from sqlalchemy.orm import Session
from passlib.hash import bcrypt
from .db import get_db, User

router = APIRouter(tags=["auth"])

def _jwt_secret() -> str:
    return os.getenv("AUTH_JWT_SECRET") or "dev-secret-change-me"

def _jwt_exp_seconds() -> int:
    try:
        return int(os.getenv("AUTH_JWT_EXPIRES_SECONDS", "3600"))
    except ValueError:
        return 3600

class SignUpReq(BaseModel):
    first_name: str = Field(min_length=1, max_length=120)
    last_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)
    phone: str | None = None
    address: str | None = None

class LoginReq(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    model_config = ConfigDict(from_attributes=True)

def _create_token(user_id: int, email: str | None) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(seconds=_jwt_exp_seconds())
    payload = {"sub": str(user_id), "email": email, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")

@router.post("/auth/signup", response_model=UserOut)
def signup(body: SignUpReq, db: Session = Depends(get_db)):
    if body.password != body.confirm_password:
        raise HTTPException(400, "passwords do not match")
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(409, "email already registered")
    user = User(
        first_name=body.first_name,
        last_name=body.last_name,
        email=body.email,
        password_hash=bcrypt.hash(body.password),
        phone=body.phone,
        address=body.address,
    )
    db.add(user); db.commit(); db.refresh(user)
    return user

@router.post("/auth/login")
def login(body: LoginReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not bcrypt.verify(body.password, user.password_hash or ""):
        raise HTTPException(status_code=401, detail="invalid credentials")
    token = _create_token(user.id, user.email)
    return {"token": token, "user": UserOut.model_validate(user).model_dump()}

def _decode(token: str) -> dict:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(401, "invalid or expired token")

@router.get("/me", response_model=UserOut)
def me(
    authorization: str | None = Header(default=None),  # 👈 read the Authorization header
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing token")
    payload = _decode(authorization.split(" ", 1)[1])
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(404, "user not found")
    return user
