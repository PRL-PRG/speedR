"""The r-benchmarks (`rbench`) and bench commits speedR runs.

Both are Python dependencies of speedR: `rbench` is pinned to a commit in
pyproject.toml, and bench comes with it at the commit rbench pins. uv.lock
records the two; the installed packages say which commits are actually in the
environment, and the two must agree before a run is recorded."""

import importlib.metadata
import json
import tomllib
from pathlib import Path

from . import REPO_ROOT

LOCK_FILE = REPO_ROOT / "uv.lock"
PACKAGES = ("rbench", "bench")


class UpstreamError(Exception):
    pass


def locked(name: str, lock: Path = LOCK_FILE) -> str:
    """The git commit uv.lock locks package `name` to."""
    with open(lock, "rb") as f:
        packages = tomllib.load(f).get("package", [])
    for p in packages:
        if p["name"] == name:
            src = p.get("source", {}).get("git", "")
            if "#" in src:
                return src.rsplit("#", 1)[1]
            raise UpstreamError(f"{lock}: {name} is not locked to a git commit")
    raise UpstreamError(f"{lock}: no {name} package")


def installed(name: str) -> str | None:
    """The git commit package `name` was installed from, if it was."""
    try:
        text = importlib.metadata.distribution(name).read_text("direct_url.json")
    except importlib.metadata.PackageNotFoundError:
        return None
    return json.loads(text or "{}").get("vcs_info", {}).get("commit_id")


def commits(lock: Path = LOCK_FILE) -> dict[str, str]:
    """{package: commit} for rbench and bench, checked against the environment."""
    out = {}
    for name in PACKAGES:
        want, have = locked(name, lock), installed(name)
        if have != want:
            raise UpstreamError(f"{name}: uv.lock has {want}, the environment has {have} "
                                "(run `uv sync`)")
        out[name] = want
    return out
