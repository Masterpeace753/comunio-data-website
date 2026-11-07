from __future__ import annotations

import json

import bcrypt
import pytest

from src.api import app as api_app
from src.api import auth
from src.config import load_settings
from src.ingest.comuniopy_client import ComunioLoginError, ComunioPyClient
from src.secret_sources import read_secret_file


def _clear_secret_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "DATABASE_URL",
        "DATABASE_URL_FILE",
        "APP_ENV",
        "COMUNIO_REQUIRE_SECRET_MODE",
        "COMUNIO_SECRET_NAME",
        "COMUNIO_SECRET_FILE",
        "COMUNIO_EMAIL",
        "COMUNIO_PASSWORD",
        "AUTH_SECRET_ARN",
        "AUTH_SECRET_FILE",
        "API_PROXY_SECRET",
        "API_PROXY_SECRET_FILE",
    ):
        monkeypatch.delenv(name, raising=False)


def test_database_url_file_reads_value_and_removes_one_final_newline(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _clear_secret_environment(monkeypatch)
    secret_file = tmp_path / "database-url"
    secret_file.write_text("postgresql://db.example/app?sslmode=verify-full\n", encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL_FILE", str(secret_file))

    assert load_settings().database_url == "postgresql://db.example/app?sslmode=verify-full"


def test_database_url_sources_are_mutually_exclusive(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    _clear_secret_environment(monkeypatch)
    secret_file = tmp_path / "database-url"
    secret_file.write_text("postgresql://db.example/app?sslmode=require", encoding="utf-8")
    monkeypatch.setenv("DATABASE_URL", "postgresql://direct/app?sslmode=require")
    monkeypatch.setenv("DATABASE_URL_FILE", str(secret_file))

    with pytest.raises(ValueError, match="only one of DATABASE_URL and DATABASE_URL_FILE"):
        load_settings()


@pytest.mark.parametrize(
    ("contents", "message"),
    [
        (None, "could not be read"),
        ("", "must not be empty"),
        ("\xff", "could not be read"),
        ("oversized", "could not be read"),
    ],
)
def test_secret_file_read_failures_are_safe(
    tmp_path, contents: str | None, message: str
) -> None:
    secret_file = tmp_path / "secret"
    if contents is not None:
        if contents == "\xff":
            secret_file.write_bytes(b"\xff")
        elif contents == "oversized":
            secret_file.write_bytes(b"x" * 1_048_577)
        else:
            secret_file.write_text(contents, encoding="utf-8")

    with pytest.raises(ValueError, match=message) as error:
        read_secret_file(str(secret_file), "TEST_SECRET_FILE")
    assert str(secret_file) not in str(error.value)
    assert not contents or contents == "oversized" or contents[:20] not in str(error.value)


def test_comunio_secret_file_works_in_production_and_parses_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _clear_secret_environment(monkeypatch)
    secret_file = tmp_path / "comunio.json"
    secret_file.write_text(
        json.dumps({"username": "league@example.test", "password": "do-not-log-this"}),
        encoding="utf-8",
    )
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("COMUNIO_SECRET_FILE", str(secret_file))

    client = ComunioPyClient(load_settings())
    credentials = client.load_credentials()

    assert (credentials.email, credentials.password, credentials.source) == (
        "league@example.test",
        "do-not-log-this",
        "secret_file",
    )


def test_comunio_secret_file_conflicts_with_other_sources(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _clear_secret_environment(monkeypatch)
    secret_file = tmp_path / "comunio.json"
    secret_file.write_text('{"username":"user","password":"password"}', encoding="utf-8")
    monkeypatch.setenv("COMUNIO_SECRET_NAME", "/comunio/aws-secret")
    monkeypatch.setenv("COMUNIO_SECRET_FILE", str(secret_file))
    with pytest.raises(ValueError, match="only one of COMUNIO_SECRET_NAME and COMUNIO_SECRET_FILE"):
        load_settings()

    monkeypatch.delenv("COMUNIO_SECRET_NAME")
    monkeypatch.setenv("COMUNIO_EMAIL", "user@example.test")
    with pytest.raises(ValueError, match="cannot be combined"):
        load_settings()


def test_comunio_aws_secret_manager_legacy_path_is_preserved(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    _clear_secret_environment(monkeypatch)
    monkeypatch.setenv("AWS_REGION", "eu-central-1")
    monkeypatch.setenv("COMUNIO_SECRET_NAME", "/comunio/credentials")
    settings = load_settings()
    calls: list[str] = []

    class FakeSecretsManager:
        def get_secret_value(self, *, SecretId: str) -> dict[str, str]:
            calls.append(SecretId)
            return {"SecretString": '{"username":"aws-user","password":"aws-password"}'}

    monkeypatch.setattr("src.ingest.comuniopy_client.boto3.client", lambda *args, **kwargs: FakeSecretsManager())
    credentials = ComunioPyClient(settings).load_credentials()

    assert calls == ["/comunio/credentials"]
    assert credentials.source == "secrets_manager"
    assert credentials.email == "aws-user"


def test_comunio_invalid_secret_file_fails_without_exposing_contents(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _clear_secret_environment(monkeypatch)
    secret_file = tmp_path / "invalid.json"
    secret_file.write_text(
        '{"username":"sensitive@example.test","password":17,"jwtSecret":"sensitive-value"}',
        encoding="utf-8",
    )
    monkeypatch.setenv("COMUNIO_SECRET_FILE", str(secret_file))

    with pytest.raises(ComunioLoginError, match="Invalid COMUNIO_SECRET_FILE contents") as error:
        ComunioPyClient(load_settings()).load_credentials()
    assert "sensitive-value" not in str(error.value)
    assert str(secret_file) not in str(error.value)


def test_auth_secret_file_and_existing_aws_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    auth.get_auth_config.cache_clear()
    _clear_secret_environment(monkeypatch)
    secret_file = tmp_path / "auth.json"
    password_hash = bcrypt.hashpw(b"test-password", bcrypt.gensalt(rounds=12)).decode()
    secret_file.write_text(
        json.dumps(
            {
                "username": "single-user",
                "passwordHash": password_hash,
                "jwtSecret": "a-jwt-secret-that-is-at-least-32-bytes",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AUTH_SECRET_FILE", str(secret_file))
    try:
        config = auth.get_auth_config()
        assert config.username == "single-user"
        assert bcrypt.checkpw(b"test-password", config.password_hash)
    finally:
        auth.get_auth_config.cache_clear()


def test_auth_secret_file_failures_are_closed_and_source_conflicts_rejected(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    auth.get_auth_config.cache_clear()
    _clear_secret_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError, match="AUTH_SECRET_ARN or AUTH_SECRET_FILE"):
        auth.get_auth_config()

    secret_file = tmp_path / "invalid-auth.json"
    secret_file.write_text("not-json", encoding="utf-8")
    monkeypatch.setenv("AUTH_SECRET_FILE", str(secret_file))
    monkeypatch.setenv("AUTH_SECRET_ARN", "arn:aws:secretsmanager:region:account:secret:auth")
    with pytest.raises(RuntimeError, match="only one of AUTH_SECRET_ARN and AUTH_SECRET_FILE"):
        auth.get_auth_config()
    auth.get_auth_config.cache_clear()

    monkeypatch.delenv("AUTH_SECRET_ARN")
    with pytest.raises(ValueError, match="Invalid authentication secret"):
        auth.get_auth_config()
    auth.get_auth_config.cache_clear()


def test_api_proxy_secret_file_production_validation_and_conflict(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    _clear_secret_environment(monkeypatch)
    proxy_file = tmp_path / "proxy-secret"
    proxy_file.write_text("proxy-secret-value\n", encoding="utf-8")
    auth_file = tmp_path / "auth.json"
    password_hash = bcrypt.hashpw(b"startup-password", bcrypt.gensalt(rounds=12)).decode()
    auth_file.write_text(
        json.dumps(
            {
                "username": "startup-user",
                "passwordHash": password_hash,
                "jwtSecret": "a-jwt-secret-that-is-at-least-32-bytes",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("API_PROXY_SECRET_FILE", str(proxy_file))
    monkeypatch.setenv("AUTH_SECRET_FILE", str(auth_file))

    auth.get_auth_config.cache_clear()
    assert api_app._load_api_proxy_secret("production") == "proxy-secret-value"
    assert auth.get_auth_config().username == "startup-user"
    auth.get_auth_config.cache_clear()

    monkeypatch.setenv("API_PROXY_SECRET", "another-value")
    with pytest.raises(ValueError, match="only one of API_PROXY_SECRET and API_PROXY_SECRET_FILE"):
        api_app._load_api_proxy_secret("production")

    monkeypatch.delenv("API_PROXY_SECRET")
    monkeypatch.delenv("API_PROXY_SECRET_FILE")
    with pytest.raises(RuntimeError, match="Production requires API_PROXY_SECRET"):
        api_app._load_api_proxy_secret("production")

    monkeypatch.setenv("API_PROXY_SECRET_FILE", str(proxy_file))
    monkeypatch.delenv("AUTH_SECRET_FILE")
    with pytest.raises(RuntimeError, match="Production requires AUTH_SECRET_ARN or AUTH_SECRET_FILE"):
        api_app._load_api_proxy_secret("production")


@pytest.mark.parametrize("file_state", ["missing", "unreadable", "invalid"])
def test_production_startup_rejects_bad_auth_secret_file_without_leaking_details(
    monkeypatch: pytest.MonkeyPatch, tmp_path, file_state: str
) -> None:
    _clear_secret_environment(monkeypatch)
    auth.get_auth_config.cache_clear()
    monkeypatch.setenv("API_PROXY_SECRET", "startup-proxy-secret")

    secret_file = tmp_path / "auth-secret"
    if file_state == "unreadable":
        secret_file.mkdir()
    elif file_state == "invalid":
        secret_file.write_text(
            '{"username":"private-user","passwordHash":"invalid","jwtSecret":"private-secret"}',
            encoding="utf-8",
        )
    monkeypatch.setenv("AUTH_SECRET_FILE", str(secret_file))

    with pytest.raises(
        RuntimeError,
        match="Production AUTH_SECRET_FILE is invalid or unavailable",
    ) as error:
        api_app._load_api_proxy_secret("production")

    assert str(secret_file) not in str(error.value)
    assert "private-secret" not in str(error.value)
    auth.get_auth_config.cache_clear()


def test_production_startup_keeps_aws_auth_provider_lazy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_secret_environment(monkeypatch)
    monkeypatch.setenv("API_PROXY_SECRET", "startup-proxy-secret")
    monkeypatch.setenv("AUTH_SECRET_ARN", "arn:aws:secretsmanager:region:account:secret:auth")
    calls: list[str] = []

    def unexpected_aws_client(*args, **kwargs):
        calls.append("called")
        raise AssertionError("AWS auth provider must remain lazy at startup")

    monkeypatch.setattr(auth.boto3, "client", unexpected_aws_client)
    auth.get_auth_config.cache_clear()

    assert api_app._load_api_proxy_secret("production") == "startup-proxy-secret"
    assert calls == []
