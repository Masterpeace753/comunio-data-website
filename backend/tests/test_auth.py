from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import pytest
from fastapi.testclient import TestClient

import src.api.app as api_app
from src.api import auth

USERNAME = "single-user"
PASSWORD = "correct horse battery staple"
JWT_SECRET = "test-jwt-secret-with-more-than-32-bytes"
ORIGIN = "http://localhost:3000"


@pytest.fixture(autouse=True)
def isolated_auth(monkeypatch, request):
    auth.reset_login_rate_limit()
    config = auth.AuthConfig(
        username=USERNAME,
        password_hash=bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=12)),
        jwt_secret=JWT_SECRET,
    )
    if request.node.name != "test_auth_secret_is_loaded_once_and_missing_production_arn_fails_closed":
        monkeypatch.setattr(auth, "get_auth_config", lambda: config)
    monkeypatch.setattr(api_app, "allowed_origins", [ORIGIN])
    yield config
    auth.reset_login_rate_limit()


@pytest.fixture
def client() -> TestClient:
    return TestClient(api_app.app, base_url="https://testserver")


def login_payload(username: str = USERNAME, password: str = PASSWORD) -> dict[str, str]:
    return {"username": username, "password": password}


def test_login_sets_secure_session_cookie_and_me_returns_user(client: TestClient) -> None:
    response = client.post("/auth/login", json=login_payload(), headers={"Origin": ORIGIN})

    assert response.status_code == 200
    assert response.json() == {"username": USERNAME}
    cookie = response.headers["set-cookie"]
    assert "token=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/" in cookie
    assert "Max-Age=28800" in cookie
    assert "Domain=" not in cookie

    me_response = client.get("/auth/me")
    assert me_response.status_code == 200
    assert me_response.json() == {"username": USERNAME}


def test_login_requires_configured_server_side_proxy_secret(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(api_app, "api_proxy_secret", "server-side-proxy-secret")
    payload = login_payload()

    missing_secret = client.post("/auth/login", json=payload, headers={"Origin": ORIGIN})
    authenticated_proxy = client.post(
        "/auth/login",
        json=payload,
        headers={"Origin": ORIGIN, "Authorization": "Bearer server-side-proxy-secret"},
    )

    assert missing_secret.status_code == 401
    assert authenticated_proxy.status_code == 200


@pytest.mark.parametrize(
    ("username", "password"),
    [("someone-else", PASSWORD), (USERNAME, "wrong-password")],
)
def test_wrong_username_or_password_returns_same_generic_401(
    client: TestClient, username: str, password: str
) -> None:
    response = client.post(
        "/auth/login",
        json=login_payload(username, password),
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password."}


def test_unknown_username_still_checks_password_with_bcrypt(client: TestClient, monkeypatch) -> None:
    calls = []
    real_checkpw = auth.bcrypt.checkpw

    def recording_checkpw(password: bytes, password_hash: bytes) -> bool:
        calls.append((password, password_hash))
        return real_checkpw(password, password_hash)

    monkeypatch.setattr(auth.bcrypt, "checkpw", recording_checkpw)
    response = client.post(
        "/auth/login",
        json=login_payload("unknown", PASSWORD),
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 401
    assert len(calls) == 1


def _unsigned_jwt() -> str:
    def encode_part(value: dict) -> str:
        data = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    return f"{encode_part({'alg': 'none', 'typ': 'JWT'})}.{encode_part({'sub': USERNAME})}."


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        _unsigned_jwt(),
        jwt.encode(
            {
                "sub": USERNAME,
                "iat": datetime.now(timezone.utc) - timedelta(hours=9),
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
                "iss": auth.JWT_ISSUER,
                "aud": auth.JWT_AUDIENCE,
            },
            JWT_SECRET,
            algorithm="HS256",
        ),
        jwt.encode(
            {
                "sub": USERNAME,
                "iat": datetime.now(timezone.utc),
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
                "iss": "wrong-issuer",
                "aud": auth.JWT_AUDIENCE,
            },
            JWT_SECRET,
            algorithm="HS256",
        ),
    ],
)
def test_invalid_expired_none_or_wrong_issuer_jwt_is_rejected(
    client: TestClient, token: str
) -> None:
    client.cookies.set(auth.TOKEN_COOKIE_NAME, token, path="/")

    response = client.get("/auth/me")

    assert response.status_code == 401


def test_missing_cookie_is_rejected(client: TestClient) -> None:
    assert client.get("/auth/me").status_code == 401


def test_login_is_throttled_after_five_attempts(client: TestClient) -> None:
    for _ in range(auth.LOGIN_ATTEMPT_LIMIT):
        response = client.post(
            "/auth/login",
            json=login_payload(password="wrong"),
            headers={"Origin": ORIGIN},
        )
        assert response.status_code == 401

    limited = client.post(
        "/auth/login",
        json=login_payload(),
        headers={"Origin": ORIGIN},
    )
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == str(auth.LOGIN_WINDOW_SECONDS)


def test_login_rate_limit_uses_cloudfront_viewer_address(client: TestClient) -> None:
    for _ in range(auth.LOGIN_ATTEMPT_LIMIT):
        response = client.post(
            "/auth/login",
            json=login_payload(password="wrong-password"),
            headers={"Origin": ORIGIN, "CloudFront-Viewer-Address": "203.0.113.5:12345"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/auth/login",
        json=login_payload(),
        headers={"Origin": ORIGIN, "CloudFront-Viewer-Address": "203.0.113.5:54321"},
    )
    allowed = client.post(
        "/auth/login",
        json=login_payload(),
        headers={"Origin": ORIGIN, "CloudFront-Viewer-Address": "203.0.113.6:12345"},
    )

    assert limited.status_code == 429
    assert allowed.status_code == 200


@pytest.mark.parametrize("origin", ["https://attacker.example", None])
def test_mutating_requests_reject_untrusted_or_missing_origin(
    client: TestClient, origin: str | None
) -> None:
    headers = {} if origin is None else {"Origin": origin}

    response = client.post("/auth/login", json=login_payload(), headers=headers)

    assert response.status_code == 403
    assert response.json()["code"] == "invalid_origin"


def test_logout_clears_cookie_with_secure_flags(client: TestClient) -> None:
    token = auth.create_access_token(USERNAME, JWT_SECRET)
    client.cookies.set(auth.TOKEN_COOKIE_NAME, token, path="/")

    response = client.post("/auth/logout", headers={"Origin": ORIGIN})

    assert response.status_code == 200
    assert response.json() == {"status": "logged_out"}
    cookie = response.headers["set-cookie"]
    assert "token=" in cookie
    assert "Max-Age=0" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/" in cookie


def test_auth_secret_is_loaded_once_and_missing_production_arn_fails_closed(monkeypatch) -> None:
    auth.get_auth_config.cache_clear()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("AUTH_SECRET_ARN", raising=False)
    with pytest.raises(RuntimeError, match="AUTH_SECRET_ARN"):
        auth.get_auth_config()

    password_hash = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=12)).decode()
    calls = []

    class FakeSecretsManager:
        def get_secret_value(self, *, SecretId: str) -> dict[str, str]:
            calls.append(SecretId)
            return {
                "SecretString": json.dumps(
                    {
                        "username": USERNAME,
                        "passwordHash": password_hash,
                        "jwtSecret": JWT_SECRET,
                    }
                )
            }

    monkeypatch.setenv("AUTH_SECRET_ARN", "arn:aws:secretsmanager:region:account:secret:auth")
    monkeypatch.setattr(auth.boto3, "client", lambda *args, **kwargs: FakeSecretsManager())
    try:
        first = auth.get_auth_config()
        second = auth.get_auth_config()
    finally:
        auth.get_auth_config.cache_clear()

    assert first is second
    assert calls == ["arn:aws:secretsmanager:region:account:secret:auth"]
