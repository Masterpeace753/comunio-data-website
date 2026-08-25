from __future__ import annotations

import src.ingest.runner as runner


class FakeClient:
    def __init__(self, settings: object) -> None:
        self.settings = settings

    def login(self) -> None:
        return None


def test_runner_accepts_scheduled_login(monkeypatch, capsys) -> None:
    monkeypatch.setattr(runner, "load_settings", lambda: object())
    monkeypatch.setattr(runner, "ComunioPyClient", FakeClient)

    result = runner.main(["--run-type", "scheduled", "--mode", "login"])

    assert result == 0
    assert "run_type=scheduled" in capsys.readouterr().out
