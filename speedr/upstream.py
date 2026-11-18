"""The r-benchmarks commit speedR runs (upstream.toml), and the bench commit
that r-benchmarks' uv.lock locks at it."""

import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path

from . import REPO_ROOT

PIN_FILE = REPO_ROOT / "upstream.toml"


class UpstreamError(Exception):
    pass


@dataclass(frozen=True)
class Pin:
    repo: str
    commit: str


def pin(path: Path = PIN_FILE) -> Pin:
    with open(path, "rb") as f:
        t = tomllib.load(f)["r-benchmarks"]
    p = Pin(repo=t["repo"], commit=t["commit"])
    if len(p.commit) != 40:
        raise UpstreamError(f"{path}: commit must be a full 40-character sha")
    return p


def bench_commit(rbench_root: Path) -> str:
    """The bench commit an r-benchmarks checkout locks, from its uv.lock."""
    with open(rbench_root / "uv.lock", "rb") as f:
        lock = tomllib.load(f)
    for p in lock.get("package", []):
        if p["name"] == "bench":
            src = p.get("source", {}).get("git", "")
            if "#" in src:
                return src.rsplit("#", 1)[1]
            raise UpstreamError(f"{rbench_root}/uv.lock: bench is not locked to a git commit")
    raise UpstreamError(f"{rbench_root}/uv.lock: no bench package")


def head(repo: Path) -> str | None:
    r = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def checkout(dest: Path, p: Pin) -> Path:
    """Check `p` out into `dest` (created, or reused if it already holds a clone)."""
    if head(dest) == p.commit:
        return dest
    if not (dest / ".git").exists():
        dest.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", "-q", str(dest)], check=True)
        subprocess.run(["git", "-C", str(dest), "remote", "add", "origin", p.repo], check=True)
    subprocess.run(["git", "-C", str(dest), "fetch", "-q", "--depth", "1", "origin", p.commit],
                   check=True)
    subprocess.run(["git", "-C", str(dest), "checkout", "-q", "--detach", "FETCH_HEAD"],
                   check=True)
    if head(dest) != p.commit:
        raise UpstreamError(f"{dest}: checked out {head(dest)}, expected {p.commit}")
    return dest
