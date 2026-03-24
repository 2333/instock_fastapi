#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
PYPROJECT_FILE = ROOT / "pyproject.toml"
WEB_PACKAGE_FILE = ROOT / "web" / "package.json"
WEB_LOCK_FILE = ROOT / "web" / "package-lock.json"

SEMVER_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)" r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)


def validate_version(version: str) -> str:
    normalized = version.strip()
    if not SEMVER_PATTERN.fullmatch(normalized):
        raise SystemExit(f"Invalid semantic version: {version}")
    return normalized


def read_repo_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def read_versions() -> dict[str, str]:
    pyproject_text = PYPROJECT_FILE.read_text(encoding="utf-8")
    pyproject_match = re.search(r'^version = "([^"]+)"$', pyproject_text, flags=re.MULTILINE)
    if not pyproject_match:
        raise SystemExit("Failed to locate project version in pyproject.toml")

    package_json = json.loads(WEB_PACKAGE_FILE.read_text(encoding="utf-8"))
    package_lock = json.loads(WEB_LOCK_FILE.read_text(encoding="utf-8"))

    return {
        "VERSION": read_repo_version(),
        "pyproject.toml": pyproject_match.group(1),
        "web/package.json": package_json["version"],
        "web/package-lock.json": package_lock["version"],
    }


def sync_version(version: str) -> None:
    normalized = validate_version(version)

    VERSION_FILE.write_text(f"{normalized}\n", encoding="utf-8")

    pyproject_text = PYPROJECT_FILE.read_text(encoding="utf-8")
    pyproject_text = re.sub(
        r'^version = "([^"]+)"$',
        f'version = "{normalized}"',
        pyproject_text,
        count=1,
        flags=re.MULTILINE,
    )
    PYPROJECT_FILE.write_text(pyproject_text, encoding="utf-8")

    package_json = json.loads(WEB_PACKAGE_FILE.read_text(encoding="utf-8"))
    package_json["version"] = normalized
    WEB_PACKAGE_FILE.write_text(
        json.dumps(package_json, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    package_lock = json.loads(WEB_LOCK_FILE.read_text(encoding="utf-8"))
    package_lock["version"] = normalized
    root_package = package_lock.get("packages", {}).get("")
    if isinstance(root_package, dict):
        root_package["version"] = normalized
    WEB_LOCK_FILE.write_text(
        json.dumps(package_lock, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def cmd_show() -> int:
    print(read_repo_version())
    return 0


def cmd_check() -> int:
    versions = read_versions()
    unique_versions = set(versions.values())
    if len(unique_versions) != 1:
        for path, version in versions.items():
            print(f"{path}: {version}", file=sys.stderr)
        raise SystemExit("Version files are out of sync")
    print(unique_versions.pop())
    return 0


def cmd_set(version: str) -> int:
    sync_version(version)
    print(validate_version(version))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage repository semantic version")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("show", help="Print the current repository version")
    subparsers.add_parser("check", help="Validate that all version files are in sync")

    set_parser = subparsers.add_parser("set", help="Set and sync a new semantic version")
    set_parser.add_argument("version", help="Semantic version, for example 0.2.0")

    args = parser.parse_args()

    if args.command == "show":
        return cmd_show()
    if args.command == "check":
        return cmd_check()
    if args.command == "set":
        return cmd_set(args.version)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
