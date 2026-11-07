"""Check published support signals for installed packages and runtime versions."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen


# The operator accepted this temporary exception until Next's ESLint plugins
# support ESLint 10. Keep it version-specific so other deprecations still fail.
NPM_EXCEPTIONS = {("eslint", "9.39.5"): "Next.js lint plugins do not yet support ESLint 10"}
INACTIVE_CLASSIFIER = "Development Status :: 7 - Inactive"


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "comunio-support-check"})
    with urlopen(request, timeout=30) as response:
        result = json.load(response)
    if not isinstance(result, dict):
        raise ValueError(f"Unexpected JSON response from {url}")
    return result


def npm_packages(lock: dict) -> list[tuple[str, str]]:
    if lock.get("lockfileVersion") not in (2, 3) or not isinstance(lock.get("packages"), dict):
        raise ValueError("An npm lockfile with package entries is required")
    packages = set()
    for path, entry in lock["packages"].items():
        if not path:
            continue
        if not isinstance(entry, dict) or entry.get("link") or "node_modules/" not in path:
            raise ValueError(f"Unsupported npm lockfile entry: {path}")
        name = entry.get("name") or path.rsplit("node_modules/", 1)[1]
        version = entry.get("version")
        resolved = entry.get("resolved")
        if not isinstance(name, str) or not isinstance(version, str) or not isinstance(resolved, str):
            raise ValueError(f"Missing package metadata: {path}")
        if not resolved.startswith("https://registry.npmjs.org/"):
            raise ValueError(f"Unsupported npm package source: {path}")
        packages.add((name, version))
    if not packages:
        raise ValueError("The npm lockfile contains no dependencies")
    return sorted(packages)


def check_npm_package(package: tuple[str, str]) -> str | None:
    name, version = package
    metadata = fetch_json(f"https://registry.npmjs.org/{quote(name, safe='')}/{quote(version, safe='')}")
    if metadata.get("name") != name or metadata.get("version") != version:
        raise ValueError(f"Unexpected npm metadata for {name}@{version}")
    deprecated = metadata.get("deprecated")
    if deprecated is not None and not isinstance(deprecated, str):
        raise ValueError(f"Invalid npm deprecation metadata for {name}@{version}")
    if not deprecated:
        return None
    if package in NPM_EXCEPTIONS:
        print(f"APPROVED EXCEPTION: {name}@{version}: {deprecated} ({NPM_EXCEPTIONS[package]})")
        return None
    return f"{name}@{version}: {deprecated}"


def check_python_package(package: tuple[str, str]) -> str | None:
    name, version = package
    metadata = fetch_json(f"https://pypi.org/pypi/{quote(name, safe='')}/{quote(version, safe='')}/json")
    info, files = metadata.get("info"), metadata.get("urls")
    if not isinstance(info, dict) or not isinstance(files, list) or not files:
        raise ValueError(f"Missing PyPI release metadata for {name}=={version}")
    canonical = lambda value: re.sub(r"[-_.]+", "-", value).lower()
    if not isinstance(info.get("name"), str) or canonical(info["name"]) != canonical(name) or info.get("version") != version:
        raise ValueError(f"Unexpected PyPI metadata for {name}=={version}")
    classifiers = info.get("classifiers")
    if not isinstance(classifiers, list) or not all(isinstance(item, str) for item in classifiers):
        raise ValueError(f"Invalid PyPI classifiers for {name}=={version}")
    if not all(isinstance(item, dict) and isinstance(item.get("yanked"), bool) for item in files):
        raise ValueError(f"Invalid PyPI yanked metadata for {name}=={version}")
    reasons = []
    if INACTIVE_CLASSIFIER in classifiers:
        reasons.append("project is marked inactive")
    if all(item["yanked"] for item in files):
        reasons.append("all release files are yanked")
    return f"{name}=={version}: {', '.join(reasons)}" if reasons else None


def check_packages(packages: list[tuple[str, str]], check) -> int:
    with ThreadPoolExecutor(max_workers=12) as executor:
        issues = [result for result in executor.map(check, packages) if result]
    for issue in issues:
        print(f"UNSUPPORTED: {issue}", file=sys.stderr)
    print(f"Checked {len(packages)} package versions; {len(issues)} unsupported.")
    return 1 if issues else 0


def runtime_cycle(product: str, version: str) -> str:
    match = re.fullmatch(r"(\d+)(?:\.(\d+))?(?:\.\d+)?", version)
    if not match:
        raise ValueError(f"Invalid {product} version: {version}")
    if product in ("python", "terraform"):
        if match.group(2) is None:
            raise ValueError(f"{product} version must include its minor version")
        return f"{match.group(1)}.{match.group(2)}"
    return match.group(1)


def check_runtime(product: str, version: str) -> int:
    cycle = runtime_cycle(product, version)
    metadata = fetch_json(f"https://endoflife.date/api/v1/products/{product}/releases/{cycle}/")
    result = metadata.get("result")
    if not isinstance(result, dict) or result.get("name") != cycle:
        raise ValueError(f"Missing lifecycle data for {product} {cycle}")
    eol, is_eol, maintained = result.get("eolFrom"), result.get("isEol"), result.get("isMaintained")
    if not isinstance(is_eol, bool) or not isinstance(maintained, bool):
        raise ValueError(f"Unknown end-of-life status for {product} {cycle}")
    if eol is not None and not isinstance(eol, str):
        raise ValueError(f"Invalid end-of-life date for {product} {cycle}")
    end = date.fromisoformat(eol) if eol else None
    if is_eol or not maintained or (end is not None and datetime.now(timezone.utc).date() >= end):
        print(f"UNSUPPORTED: {product} {version}; end of life {end or 'not published'}, maintained={maintained}", file=sys.stderr)
        return 1
    print(f"Supported: {product} {version}; end of life {end or 'not yet announced'}")
    return 0


def check_next_react(next_version: str, react_version: str) -> int:
    next_major = int(runtime_cycle("nextjs", next_version))
    react_major = int(runtime_cycle("react", react_version))
    if next_major >= 16 and react_major < 19:
        print(f"UNSUPPORTED: Next.js {next_version} deprecates React {react_version}; use React 19 or later", file=sys.stderr)
        return 1
    print(f"Next.js {next_version} and React {react_version} pass the deprecation policy")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="check", required=True)
    npm = subparsers.add_parser("npm")
    npm.add_argument("lockfile", type=Path)
    subparsers.add_parser("python-packages")
    runtime = subparsers.add_parser("runtime")
    runtime.add_argument("product", choices=("nodejs", "python", "postgresql", "terraform", "nextjs", "react"))
    runtime.add_argument("version")
    next_react = subparsers.add_parser("next-react")
    next_react.add_argument("next_version")
    next_react.add_argument("react_version")
    args = parser.parse_args()
    if args.check == "runtime":
        return check_runtime(args.product, args.version)
    if args.check == "next-react":
        return check_next_react(args.next_version, args.react_version)
    if args.check == "npm":
        with args.lockfile.open(encoding="utf-8") as file:
            return check_packages(npm_packages(json.load(file)), check_npm_package)
    installed = {(dist.metadata["Name"], dist.version) for dist in importlib.metadata.distributions()}
    if not installed or any(not name or not version for name, version in installed):
        raise ValueError("Installed Python package metadata is incomplete")
    return check_packages(sorted(installed), check_python_package)


if __name__ == "__main__":
    sys.exit(main())
