from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT_DIR / "VERSION"
DEFAULT_VERSION = "0.0.0-dev"
DEFAULT_GIT_SHA = "local"


def _read_version_file() -> str:
    if not VERSION_FILE.exists():
        return DEFAULT_VERSION
    value = VERSION_FILE.read_text(encoding="utf-8").strip()
    return value or DEFAULT_VERSION


@dataclass(frozen=True)
class BuildInfo:
    version: str
    git_sha: str

    @property
    def release(self) -> str:
        return f"v{self.version}"

    def to_dict(self) -> dict[str, str]:
        payload = asdict(self)
        payload["release"] = self.release
        return payload


@lru_cache
def get_build_info() -> BuildInfo:
    return BuildInfo(
        version=os.getenv("APP_VERSION") or _read_version_file(),
        git_sha=os.getenv("APP_GIT_SHA") or DEFAULT_GIT_SHA,
    )
