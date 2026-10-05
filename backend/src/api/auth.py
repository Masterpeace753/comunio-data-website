from __future__ import annotations

import hmac
import json
import os
import re
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from ipaddress import ip_address
from typing import Annotated

import bcrypt
import boto3
import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

TOKEN_COOKIE_NAME = "token"
SESSION_TTL_SECONDS = 8 * 60 * 60
JWT_ISSUER = "comunio-data-api"
JWT_AUDIENCE = "comunio-data-website"
LOGIN_ATTEMPT_LIMIT = 5
LOGIN_WINDOW_SECONDS = 5 * 60
MAX_TRACKED_LOGIN_IPS = 10_000


@dataclass(frozen=True)
class AuthConfig:
    username: str
    password_hash: bytes
    jwt_secret: str


@lru_cache(maxsize=1)
def get_auth_config() -> AuthConfig:
    """Load the single-user credentials once per process from Secrets Manager."""
    secret_arn = os.getenv("AUTH_SECRET_ARN")
    if not secret_arn:
        if os.getenv("APP_ENV", "dev").strip().lower() in {"prod", "production"}:
            raise RuntimeError("AUTH_SECRET_ARN is required in production")
        raise RuntimeError("Authentication is not configured")

    client = boto3.client("secretsmanager", region_name=os.getenv("AWS_REGION"))
    secret_string = client.get_secret_value(SecretId=secret_arn)["SecretString"]
    value = json.loads(secret_string)
    username = value["username"]
    password_hash = value["passwordHash"]
    jwt_secret = value["jwtSecret"]
    if (
        not isinstance(username, str)
        or not username
        or not isinstance(password_hash, str)
        or not isinstance(jwt_secret, str)
        or len(jwt_secret.encode("utf-8")) < 32
    ):
        raise ValueError("Invalid authentication secret")
    # Fail closed for malformed password hashes instead of weakening verification.
    encoded_hash = password_hash.encode("utf-8")
    if not re.fullmatch(rb"\$2[aby]\$12\$[./A-Za-z0-9]{53}", encoded_hash):
        raise ValueError("Invalid authentication secret")
    return AuthConfig(username, encoded_hash, jwt_secret)


_DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"dummy-auth-password", bcrypt.gensalt(rounds=12))
_attempts: dict[str, deque[float]] = {}
_attempts_lock = threading.Lock()


def reset_login_rate_limit() -> None:
    """Reset process-local state; primarily useful for isolated test processes."""
    with _attempts_lock:
        _attempts.clear()


def _consume_login_attempt(ip_address: str, now: float | None = None) -> bool:
    current_time = time.monotonic() if now is None else now
    with _attempts_lock:
        attempts = _attempts.get(ip_address)
        if attempts is None:
            if len(_attempts) >= MAX_TRACKED_LOGIN_IPS:
                _attempts.pop(next(iter(_attempts)))
            attempts = _attempts[ip_address] = deque()
        while attempts and current_time - attempts[0] >= LOGIN_WINDOW_SECONDS:
            attempts.popleft()
        if not attempts:
            _attempts.pop(ip_address, None)
            attempts = _attempts[ip_address] = deque()
        if len(attempts) >= LOGIN_ATTEMPT_LIMIT:
            return False
        attempts.append(current_time)
        return True


def _login_client_ip(request: Request) -> str:
    viewer_address = request.headers.get("cloudfront-viewer-address")
    if viewer_address:
        address, _, _port = viewer_address.strip().rpartition(":")
        try:
            return str(ip_address(address.strip("[]")))
        except ValueError:
            pass
    return request.client.host if request.client else "unknown"


def create_access_token(username: str, jwt_secret: str, now: datetime | None = None) -> str:
    issued_at = now or datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": username,
            "iat": issued_at,
            "exp": issued_at + timedelta(seconds=SESSION_TTL_SECONDS),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        },
        jwt_secret,
        algorithm="HS256",
    )


def validate_access_token(token: str, jwt_secret: str) -> str | None:
    try:
        claims = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except (jwt.InvalidTokenError, TypeError, ValueError):
        return None
    username = claims.get("sub")
    return username if isinstance(username, str) and username else None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=1024)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, str]:
    if not _consume_login_attempt(_login_client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts.",
            headers={"Retry-After": str(LOGIN_WINDOW_SECONDS)},
        )

    try:
        config = get_auth_config()
    except Exception as exc:
        # Never expose AWS errors, secret values, or parser details.
        raise HTTPException(status_code=503, detail="Authentication is unavailable.") from exc

    supplied_username = payload.username.encode("utf-8")
    configured_username = config.username.encode("utf-8")
    username_matches = hmac.compare_digest(supplied_username, configured_username)
    candidate_hash = config.password_hash if username_matches else _DUMMY_PASSWORD_HASH
    try:
        password_matches = bcrypt.checkpw(payload.password.encode("utf-8"), candidate_hash)
    except (ValueError, TypeError):
        password_matches = False
    if not (username_matches and password_matches):
        raise _unauthorized()

    response.set_cookie(
        key=TOKEN_COOKIE_NAME,
        value=create_access_token(config.username, config.jwt_secret),
        max_age=SESSION_TTL_SECONDS,
        path="/",
        secure=True,
        httponly=True,
        samesite="strict",
    )
    return {"username": config.username}


def require_authenticated_user(
    request: Request,
) -> str:
    config = get_auth_config()
    token = request.cookies.get(TOKEN_COOKIE_NAME)
    if not token:
        raise _unauthorized()
    username = validate_access_token(token, config.jwt_secret)
    if username is None:
        raise _unauthorized()
    return username


@router.get("/me")
def me(username: Annotated[str, Depends(require_authenticated_user)]) -> dict[str, str]:
    return {"username": username}


@router.post("/logout")
def logout(
    response: Response,
    _username: Annotated[str, Depends(require_authenticated_user)],
) -> dict[str, str]:
    response.delete_cookie(
        key=TOKEN_COOKIE_NAME,
        path="/",
        secure=True,
        httponly=True,
        samesite="strict",
    )
    return {"status": "logged_out"}
