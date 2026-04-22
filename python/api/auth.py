"""
Auth real para Edgebet — registro, login, me.
bcrypt para passwords + JWT para sesiones.
"""
from __future__ import annotations

import os
import psycopg2
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from api.db import connect

# === Config ===
SECRET_KEY = os.environ.get("EDGEBET_JWT_SECRET", "edgebet-dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_HOURS = 24 * 7  # 7 días
BCRYPT_MAX_BYTES = 72  # bcrypt trunca en 72 bytes — validamos antes

bearer_scheme = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/auth", tags=["auth"])


# === Schemas ===
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    id: int
    email: str
    name: str
    tier: str
    created_at: str
    onboarding_done: bool


class AuthResponse(BaseModel):
    token: str
    user: UserPublic


# === Helpers ===
def _hash_password(pw: str) -> str:
    # bcrypt truncates past 72 bytes; caller enforces a max on UX side.
    pw_bytes = pw.encode("utf-8")[:BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def _verify_password(pw: str, hashed: str) -> bool:
    try:
        pw_bytes = pw.encode("utf-8")[:BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))
    except ValueError:
        return False


def _create_token(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _row_to_user(row) -> UserPublic:
    return UserPublic(
        id=row["id"],
        email=row["email"],
        name=row["name"],
        tier=row["tier"],
        created_at=row["created_at"],
        onboarding_done=bool(row["onboarding_done"]) if "onboarding_done" in row.keys() else False,
    )


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> UserPublic:
    if creds is None:
        raise HTTPException(status_code=401, detail="No token provided")
    try:
        payload = jwt.decode(creds.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")

    with connect() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return _row_to_user(row)


# === Routes ===
@router.post("/register", response_model=AuthResponse, status_code=201)
def register(body: RegisterRequest) -> AuthResponse:
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be ≥ 6 characters")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")

    email_norm = body.email.lower()
    try:
        with connect() as cur:
            cur.execute(
                "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s) RETURNING id",
                (email_norm, _hash_password(body.password), body.name.strip()),
            )
            user_id = cur.fetchone()["id"]
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
    except psycopg2.IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = _row_to_user(row)
    return AuthResponse(token=_create_token(user.id, user.email), user=user)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest) -> AuthResponse:
    email_norm = body.email.lower()
    with connect() as cur:
        cur.execute("SELECT * FROM users WHERE email = %s", (email_norm,))
        row = cur.fetchone()

    if row is None or not _verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = _row_to_user(row)
    return AuthResponse(token=_create_token(user.id, user.email), user=user)


@router.get("/me", response_model=UserPublic)
def me(user: Annotated[UserPublic, Depends(get_current_user)]) -> UserPublic:
    return user
