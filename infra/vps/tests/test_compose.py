"""Validate the rendered VPS deployment without starting containers."""

import json
import os
import subprocess
import unittest
from pathlib import Path


VPS_DIR = Path(__file__).resolve().parents[1]
TEST_ENV = {
    "POSTGRES_IMAGE": "postgres:16",
    "POSTGRES_UID": "999",
    "POSTGRES_GID": "999",
    "PGDATA": "/var/lib/postgresql/data",
    "INGEST_IMAGE": "example.invalid/ingest:ci",
    "API_IMAGE": "example.invalid/api:ci",
    "APP_UID": "10001",
    "APP_GID": "10001",
    "VPS_SECRET_DIR": "/tmp/comunio-ci-secrets",
    "VPS_TLS_DIR": "/tmp/comunio-ci-tls",
    "API_ALLOWED_ORIGINS": "https://example.invalid",
    "INGEST_RUN_TYPE": "scheduled",
    "COMPOSE_DISABLE_ENV_FILE": "1",
    "COMPOSE_PROFILES": "",
}


def compose_command(*profiles: str) -> list[str]:
    command = ["docker", "compose", "--project-directory", str(VPS_DIR), "-f", str(VPS_DIR / "compose.yaml")]
    for profile in profiles:
        command.extend(["--profile", profile])
    command.extend(["config", "--format", "json"])
    return command


def rendered_config(*profiles: str) -> dict:
    result = subprocess.run(
        compose_command(*profiles),
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **TEST_ENV},
    )
    return json.loads(result.stdout)


class ComposeConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.default = rendered_config()
        cls.all_profiles = rendered_config("bootstrap", "jobs", "api")

    def test_default_only_starts_database(self) -> None:
        self.assertEqual(set(self.default["services"]), {"db"})

    def test_profiles_are_opt_in(self) -> None:
        for profiles, expected in (
            (("bootstrap",), {"db", "db-volume-init", "db-initdb"}),
            (("jobs",), {"db", "ingest"}),
            (("api",), {"db", "api"}),
            (("jobs", "api"), {"db", "ingest", "api"}),
        ):
            with self.subTest(profiles=profiles):
                self.assertEqual(set(rendered_config(*profiles)["services"]), expected)

    def test_required_inputs_fail_closed(self) -> None:
        for name in (
            "POSTGRES_IMAGE", "POSTGRES_UID", "POSTGRES_GID", "PGDATA",
            "INGEST_IMAGE", "APP_UID", "APP_GID", "VPS_SECRET_DIR", "VPS_TLS_DIR",
        ):
            for value in (None, ""):
                with self.subTest(name=name, value=value):
                    environment = {**os.environ, **TEST_ENV}
                    environment.pop(name, None)
                    if value is not None:
                        environment[name] = value
                    result = subprocess.run(
                        compose_command("bootstrap", "jobs", "api"),
                        capture_output=True,
                        text=True,
                        env=environment,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(name, result.stderr)

    def test_profiles_and_network_boundaries(self) -> None:
        config = self.all_profiles
        self.assertEqual(set(config["services"]), {"db", "db-volume-init", "db-initdb", "ingest", "api"})
        self.assertTrue(config["networks"]["database"]["internal"])
        self.assertEqual(set(config["services"]["api"]["networks"]), {"database"})
        self.assertEqual(set(config["services"]["db"]["networks"]), {"database"})
        self.assertEqual(set(config["services"]["ingest"]["networks"]), {"database", "outbound"})
        for name, service in config["services"].items():
            with self.subTest(service=name):
                self.assertFalse(service.get("ports"))
                self.assertFalse(service.get("privileged", False))
                self.assertNotEqual(service.get("network_mode"), "host")
                self.assertNotEqual(service.get("pid"), "host")
                self.assertTrue(service.get("read_only"))
                self.assertIn("ALL", service.get("cap_drop", []))
                self.assertIn("no-new-privileges:true", service.get("security_opt", []))
                self.assertTrue(service.get("pids_limit"))
                self.assertFalse(any("/var/run/docker.sock" in str(mount) for mount in service.get("volumes", [])))

    def test_process_users_and_bootstrap_capabilities(self) -> None:
        services = self.all_profiles["services"]
        for name in ("db", "db-initdb", "ingest", "api"):
            with self.subTest(service=name):
                uid, gid = services[name]["user"].split(":")
                self.assertTrue(uid.isdecimal() and int(uid) > 0)
                self.assertTrue(gid.isdecimal() and int(gid) > 0)
                self.assertFalse(services[name].get("cap_add"))
        helper = services["db-volume-init"]
        self.assertEqual(helper["user"], "0:0")
        self.assertEqual(set(helper["cap_add"]), {"CHOWN", "FOWNER"})
        self.assertEqual(helper["network_mode"], "none")
        self.assertEqual(len(helper["volumes"]), 1)
        self.assertEqual(helper["volumes"][0]["type"], "volume")
        self.assertEqual(helper["volumes"][0]["target"], TEST_ENV["PGDATA"])
        self.assertEqual(services["db-initdb"]["network_mode"], "none")
        mounts = services["db-initdb"]["volumes"]
        self.assertEqual(len(mounts), 1)
        self.assertEqual(mounts[0]["type"], "volume")
        self.assertEqual(mounts[0]["source"], helper["volumes"][0]["source"])
        self.assertEqual(mounts[0]["target"], TEST_ENV["PGDATA"])

    def test_secret_mounts_are_read_only_and_separated(self) -> None:
        services = self.all_profiles["services"]
        for name in ("db", "ingest", "api"):
            with self.subTest(service=name):
                bindings = [mount for mount in services[name]["volumes"] if mount["type"] == "bind"]
                self.assertTrue(bindings)
                self.assertTrue(all(mount.get("read_only") for mount in bindings))
        ingest_sources = {mount["source"] for mount in services["ingest"]["volumes"] if mount["type"] == "bind"}
        api_sources = {mount["source"] for mount in services["api"]["volumes"] if mount["type"] == "bind"}
        self.assertIn("/tmp/comunio-ci-secrets/comunio.json", ingest_sources)
        self.assertNotIn("/tmp/comunio-ci-secrets/comunio.json", api_sources)
        for name in ("api-auth.json", "api-proxy-secret", "api-database-url"):
            source = f"/tmp/comunio-ci-secrets/{name}"
            self.assertIn(source, api_sources)
            self.assertNotIn(source, ingest_sources)

    def test_runtime_contract(self) -> None:
        services = self.all_profiles["services"]
        self.assertEqual(services["ingest"]["environment"]["TZ"], "UTC")
        self.assertEqual(services["ingest"]["environment"]["COMUNIO_SECRET_FILE"], "/run/secrets/comunio.json")
        self.assertEqual(services["ingest"]["environment"]["DATABASE_URL_FILE"], "/run/secrets/database-url")
        self.assertEqual(services["api"]["environment"]["AUTH_SECRET_FILE"], "/run/secrets/auth.json")
        self.assertEqual(services["api"]["environment"]["API_PROXY_SECRET_FILE"], "/run/secrets/api-proxy-secret")
        self.assertIn("ssl=on", services["db"]["command"])
        self.assertEqual(services["ingest"]["depends_on"]["db"]["condition"], "service_healthy")
        self.assertEqual(services["api"]["depends_on"]["db"]["condition"], "service_healthy")


if __name__ == "__main__":
    unittest.main()
