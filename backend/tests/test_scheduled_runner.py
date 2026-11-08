from __future__ import annotations

from dataclasses import dataclass

import pytest

import src.ingest.runner as runner
from src.ingest.comuniopy_client import ComunioLoginError, ComunioSnapshotError


@dataclass
class FakeSettings:
    database_url: str = ""
    login_retry_attempts: int = 3
    login_retry_wait_seconds: int = 300


class FakeClient:
    def __init__(self, settings: object) -> None:
        self.settings = settings

    def login(self) -> None:
        return None


def test_runner_accepts_scheduled_login(monkeypatch, capsys) -> None:
    monkeypatch.setattr(runner, "load_settings", lambda: FakeSettings())
    monkeypatch.setattr(runner, "ComunioPyClient", FakeClient)

    result = runner.main(["--run-type", "scheduled", "--mode", "login"])

    assert result == 0
    assert "run_type=scheduled" in capsys.readouterr().out


def test_login_with_retry_succeeds_after_transient_failures(capsys) -> None:
    attempts: list[int] = []

    class FlakyClient:
        def login(self) -> None:
            attempts.append(1)
            if len(attempts) < 2:
                raise ComunioLoginError("temporary failure")

    sleeps: list[int] = []
    runner._login_with_retry(FlakyClient(), max_attempts=3, wait_seconds=300, sleep_fn=sleeps.append)

    assert len(attempts) == 2
    assert sleeps == [300]
    assert "login_recovered" in capsys.readouterr().out


def test_login_with_retry_gives_up_after_max_attempts(capsys) -> None:
    class AlwaysFailingClient:
        def login(self) -> None:
            raise ComunioLoginError("bad credentials")

    sleeps: list[int] = []

    try:
        runner._login_with_retry(AlwaysFailingClient(), max_attempts=3, wait_seconds=300, sleep_fn=sleeps.append)
        assert False, "expected ComunioLoginError"
    except ComunioLoginError:
        pass

    assert sleeps == [300, 300]
    out = capsys.readouterr().out
    assert out.count("login_attempt_failed") == 3


def test_run_failed_after_exhausted_login_retries(monkeypatch, capsys) -> None:
    class AlwaysFailingClient:
        def __init__(self, settings: object) -> None:
            self.settings = settings

        def login(self) -> None:
            raise ComunioLoginError("bad credentials")

    monkeypatch.setattr(
        runner,
        "load_settings",
        lambda: FakeSettings(login_retry_attempts=2, login_retry_wait_seconds=0),
    )
    monkeypatch.setattr(runner, "ComunioPyClient", AlwaysFailingClient)

    result = runner.main(["--run-type", "scheduled", "--mode", "login"])

    assert result == 1
    out = capsys.readouterr().out
    assert "run_failed" in out
    assert "stage=login" in out


def test_run_failed_login_sanitizes_sensitive_exception_text(monkeypatch, capsys) -> None:
    sensitive = (
        "postgresql://user:S3cr3t@host:5432/db "
        "Authorization: Bearer eyJhbGciOi... "
        "arn:aws:iam::123456789012:role/comunio-task-role "
        "C:\\Users\\alice\\secrets.json alice@example.com"
    )

    class LeakyClient:
        def __init__(self, settings: object) -> None:
            self.settings = settings

        def login(self) -> None:
            raise ComunioLoginError(sensitive)

    monkeypatch.setattr(
        runner,
        "load_settings",
        lambda: FakeSettings(login_retry_attempts=1, login_retry_wait_seconds=0),
    )
    monkeypatch.setattr(runner, "ComunioPyClient", LeakyClient)

    result = runner.main(["--run-type", "scheduled", "--mode", "login"])

    assert result == 1
    out = capsys.readouterr().out
    assert sensitive not in out
    assert "S3cr3t" not in out
    assert "Bearer" not in out
    assert "arn:aws" not in out
    assert "alice@example.com" not in out
    assert "detail=authentication_failed" in out


class TrackingConnection:
    def __init__(self) -> None:
        self.started_rows: list[tuple] = []
        self.failed_rows: list[tuple] = []
        self.stages: list[tuple] = []
        self.closed = False

    def cursor(self):
        return TrackingCursor(self)

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class TrackingCursor:
    def __init__(self, connection: TrackingConnection) -> None:
        self.connection = connection
        self.result = None

    def __enter__(self) -> "TrackingCursor":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        return None

    def execute(self, query: str, parameters: tuple) -> None:
        if "INSERT INTO ingest_runs" in query:
            self.connection.started_rows.append(parameters)
            self.result = (73,)
        elif "UPDATE ingest_runs" in query:
            if "error_code = %s" in query:
                self.connection.failed_rows.append(parameters)
            else:
                self.connection.stages.append(parameters)

    def fetchone(self):
        return self.result


def test_snapshot_attempt_is_persisted_when_login_fails(monkeypatch, capsys) -> None:
    connection = TrackingConnection()
    sensitive = "password=do-not-persist"

    class FailedLoginClient:
        def __init__(self, settings: object) -> None:
            pass

        def login(self) -> None:
            raise ComunioLoginError(sensitive)

    monkeypatch.setattr(
        runner,
        "load_settings",
        lambda: FakeSettings(database_url="postgres://db", login_retry_attempts=1),
    )
    monkeypatch.setattr(runner, "connect", lambda _url: connection)
    monkeypatch.setattr(runner, "ComunioPyClient", FailedLoginClient)

    result = runner.main(["--run-type", "scheduled"])

    assert result == 1
    assert len(connection.started_rows) == 1
    assert connection.started_rows[0][0] == "scheduled"
    assert connection.started_rows[0][2] == "login"
    assert (connection.failed_rows[0][0], connection.failed_rows[0][3]) == ("failed", "login")
    assert connection.failed_rows[0][4] == "authentication_failed"
    assert sensitive not in repr(connection.started_rows + connection.failed_rows)
    assert connection.closed
    assert "detail=authentication_failed" in capsys.readouterr().out


def test_snapshot_attempt_is_persisted_when_fetch_fails(monkeypatch, capsys) -> None:
    connection = TrackingConnection()

    class FailedSnapshotClient:
        def __init__(self, settings: object) -> None:
            pass

        def login(self) -> None:
            return None

        def fetch_snapshot(self) -> dict:
            raise ComunioSnapshotError("sensitive upstream response")

    monkeypatch.setattr(runner, "load_settings", lambda: FakeSettings(database_url="postgres://db"))
    monkeypatch.setattr(runner, "connect", lambda _url: connection)
    monkeypatch.setattr(runner, "ComunioPyClient", FailedSnapshotClient)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)

    result = runner.main(["--run-type", "manual"])

    assert result == 1
    assert connection.started_rows[0][0] == "manual"
    assert connection.stages == [("snapshot", 73)]
    assert (connection.failed_rows[0][0], connection.failed_rows[0][3]) == ("failed", "snapshot")
    assert connection.failed_rows[0][4] == "snapshot_fetch_failed"
    assert "sensitive upstream response" not in repr(connection.failed_rows)
    assert connection.closed
    assert "detail=snapshot_fetch_failed" in capsys.readouterr().out


def test_safe_detail_falls_back_for_unmapped_stage() -> None:
    assert runner._safe_error_code("config") == "unexpected_error"
    assert runner._safe_error_code("login") == "authentication_failed"
    assert runner._safe_error_code("snapshot") == "snapshot_fetch_failed"
    assert runner._safe_error_code("persistence") == "database_persistence_failed"


def test_fetch_with_backoff_recovers_after_transient_snapshot_errors(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    attempts: list[int] = []

    class FlakyClient:
        def fetch_snapshot(self) -> dict:
            attempts.append(1)
            if len(attempts) < 3:
                raise ComunioSnapshotError("temporary snapshot failure")
            return {"teams": [], "players": [], "market_values": []}

    sleeps: list[int] = []
    monkeypatch.setattr(runner.time, "sleep", sleeps.append)
    result = runner._fetch_with_backoff(FlakyClient(), attempts=4)

    assert result == {"teams": [], "players": [], "market_values": []}
    assert len(attempts) == 3
    assert sleeps == [2, 4]

    assert capsys.readouterr().out.count("snapshot_retry") == 2


def test_fetch_with_backoff_stops_after_max_attempts(monkeypatch, capsys) -> None:
    class AlwaysFailingClient:
        def fetch_snapshot(self) -> dict:
            raise ComunioSnapshotError("temporary snapshot failure")

    sleeps: list[int] = []
    monkeypatch.setattr(runner.time, "sleep", sleeps.append)

    try:
        runner._fetch_with_backoff(AlwaysFailingClient(), attempts=3)
        assert False, "expected ComunioSnapshotError"
    except ComunioSnapshotError as exc:
        assert "after 3 attempts" in str(exc)

    assert sleeps == [2, 4]
    assert capsys.readouterr().out.count("snapshot_retry") == 2
