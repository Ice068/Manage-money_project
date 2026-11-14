from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, Field

SESSION_COOKIE = "money_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 12
PASSWORD_HASHER = PasswordHash.recommended()


@dataclass(frozen=True)
class AuthSettings:
    username: str
    password_hash: str
    secret_key: str
    secure_cookie: bool

    @property
    def serializer(self) -> URLSafeTimedSerializer:
        return URLSafeTimedSerializer(self.secret_key, salt="money-tracker-session-v1")


class LoginPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Annotated[str, Field(min_length=1, max_length=100)]
    password: Annotated[str, Field(min_length=1, max_length=1024)]


def load_auth_settings() -> AuthSettings | None:
    import os

    values = {
        "username": os.getenv("APP_USERNAME", ""),
        "password_hash": os.getenv("APP_PASSWORD_HASH", ""),
        "secret_key": os.getenv("APP_SECRET_KEY", ""),
    }
    if not any(values.values()):
        return None
    if not all(values.values()):
        raise RuntimeError("APP_USERNAME, APP_PASSWORD_HASH and APP_SECRET_KEY must all be set")
    if len(values["secret_key"]) < 32:
        raise RuntimeError("APP_SECRET_KEY must contain at least 32 characters")
    if not values["password_hash"].startswith("$argon2id$"):
        raise RuntimeError("APP_PASSWORD_HASH must be an Argon2id hash")

    return AuthSettings(
        username=values["username"],
        password_hash=values["password_hash"],
        secret_key=values["secret_key"],
        secure_cookie=os.getenv("APP_ENV", "development").lower() == "production",
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return PASSWORD_HASHER.verify(password, password_hash)
    except Exception:
        return False


def verify_session(token: str | None, settings: AuthSettings) -> bool:
    if not token:
        return False
    try:
        payload = settings.serializer.loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return False
    return isinstance(payload, dict) and secrets.compare_digest(
        str(payload.get("sub", "")), settings.username
    )


def build_auth_router(settings: AuthSettings | None) -> APIRouter:
    router = APIRouter()
    recent_failures: dict[str, list[float]] = {}
    password_hasher = PASSWORD_HASHER

    @router.get("/status")
    def auth_status(request: Request) -> dict[str, bool]:
        return {
            "auth_enabled": settings is not None,
            "authenticated": bool(
                settings is not None
                and verify_session(request.cookies.get(SESSION_COOKIE), settings)
            ),
        }

    @router.post("/login")
    def login(payload: LoginPayload, request: Request, response: Response) -> dict[str, bool]:
        if settings is None:
            return {"authenticated": True}

        now = time.monotonic()
        client_ip = request.client.host if request.client else "unknown"
        for address, stamps in list(recent_failures.items()):
            active_stamps = [stamp for stamp in stamps if now - stamp < 900]
            if active_stamps:
                recent_failures[address] = active_stamps
            else:
                recent_failures.pop(address, None)
        if client_ip not in recent_failures and len(recent_failures) >= 2048:
            recent_failures.pop(next(iter(recent_failures)))
        attempts = [stamp for stamp in recent_failures.get(client_ip, []) if now - stamp < 900]
        recent_failures[client_ip] = attempts
        if len(attempts) >= 5:
            raise HTTPException(status_code=429, detail="ลองเข้าสู่ระบบใหม่ภายหลัง")

        username_valid = secrets.compare_digest(payload.username, settings.username)
        password_valid = password_hasher.verify(payload.password, settings.password_hash)
        if not username_valid or not password_valid:
            attempts.append(now)
            recent_failures[client_ip] = attempts
            raise HTTPException(status_code=401, detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

        recent_failures.pop(client_ip, None)
        response.set_cookie(
            key=SESSION_COOKIE,
            value=settings.serializer.dumps({"sub": settings.username}),
            max_age=SESSION_MAX_AGE_SECONDS,
            httponly=True,
            secure=settings.secure_cookie,
            samesite="strict",
            path="/",
        )
        return {"authenticated": True}

    @router.post("/logout")
    def logout(response: Response) -> dict[str, bool]:
        response.delete_cookie(
            key=SESSION_COOKIE,
            path="/",
            httponly=True,
            secure=bool(settings and settings.secure_cookie),
            samesite="strict",
        )
        return {"authenticated": False}

    return router


def hash_password(password: str) -> str:
    return PASSWORD_HASHER.hash(password)
