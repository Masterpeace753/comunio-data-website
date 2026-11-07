"""Check the timer and service contract without running the scheduler."""

import configparser
import unittest
from pathlib import Path


SYSTEMD_DIR = Path(__file__).resolve().parents[1] / "systemd"


def read_unit(name: str) -> configparser.ConfigParser:
    config = configparser.ConfigParser(interpolation=None, strict=True)
    if not config.read(SYSTEMD_DIR / name, encoding="utf-8"):
        raise FileNotFoundError(name)
    return config


class SystemdConfigurationTests(unittest.TestCase):
    def test_timer_uses_persistent_utc_schedule(self) -> None:
        timer = read_unit("comunio-ingest.timer")["Timer"]
        self.assertEqual(timer["OnCalendar"], "*-*-* 06:00:00 UTC")
        self.assertEqual(timer["Persistent"], "true")
        self.assertEqual(timer["Unit"], "comunio-ingest@scheduled.service")

    def test_manual_and_scheduled_instances_share_lock(self) -> None:
        service = read_unit("comunio-ingest@.service")["Service"]
        self.assertEqual(service["Type"], "oneshot")
        self.assertEqual(service["Environment"], "INGEST_RUN_TYPE=%i")
        self.assertIn("/usr/bin/flock -n -E 75 %t/comunio-ingest.lock ", service["ExecStart"])
        self.assertIn("--profile jobs run --rm ingest", service["ExecStart"])
        self.assertEqual(service["TimeoutStartSec"], "30min")


if __name__ == "__main__":
    unittest.main()
