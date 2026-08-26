from __future__ import annotations

from dataclasses import dataclass

import src.ingest.runner as runner
from src.ingest.comuniopy_client import ComunioLoginError


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

