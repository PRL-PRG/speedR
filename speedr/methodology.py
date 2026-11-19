"""Methodology versions (methodology/versions.csv): what decides what a number
means. Every run records the version it was measured under, and results from
two versions are never compared. 0.x versions are drafts; a frozen version
never changes (methodology/README.md)."""

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from . import REPO_ROOT

METHODOLOGY_DIR = REPO_ROOT / "methodology"
STATUS = {"draft", "frozen"}
VERSION = re.compile(r"^[0-9]+\.[0-9]+$")


class MethodologyError(ValueError):
    pass


@dataclass(frozen=True)
class Methodology:
    version: str
    status: str
    date: str
    summary: str

    @property
    def key(self) -> tuple[int, int]:
        major, minor = self.version.split(".")
        return int(major), int(minor)


def load_all(directory: Path = METHODOLOGY_DIR) -> list[Methodology]:
    """Every version, oldest first; checks each has a known status and a text."""
    with open(directory / "versions.csv", newline="") as f:
        versions = [Methodology(**row) for row in csv.DictReader(f)]
    for m in versions:
        if not VERSION.match(m.version):
            raise MethodologyError(f"{m.version!r}: a version is MAJOR.MINOR")
        if m.status not in STATUS:
            raise MethodologyError(f"{m.version}: status must be one of {sorted(STATUS)}")
        if not (directory / f"{m.version}.qmd").is_file():
            raise MethodologyError(f"{m.version}: no {m.version}.qmd beside versions.csv")
    if not versions:
        raise MethodologyError("versions.csv lists no version")
    if len({m.version for m in versions}) != len(versions):
        raise MethodologyError("versions.csv lists a version twice")
    return sorted(versions, key=lambda m: m.key)


def current(directory: Path = METHODOLOGY_DIR) -> Methodology:
    """The newest version: the one new runs are measured under."""
    return load_all(directory)[-1]
