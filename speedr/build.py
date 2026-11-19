"""How every R version is built (build/settings.toml): the build environment of
one version is the settings of the rules whose range contains it, in order.

A version is what a source tree's VERSION file declares, e.g. "4.6.2" or
"4.7.0 Under development (unstable)"; only its number counts, so a snapshot of
R-devel gets the rules of the release it leads up to."""

import re
import tomllib
from pathlib import Path

from . import REPO_ROOT

SETTINGS_FILE = REPO_ROOT / "build" / "settings.toml"
COMPILERS = {"cc": "gcc", "cxx": "g++", "fc": "gfortran"}
KEYS = {"why", "from", "until", "configure", *COMPILERS}


class BuildError(ValueError):
    pass


def key(version: str) -> tuple[int, ...]:
    m = re.match(r"\s*(\d+(?:\.\d+)*)", version)
    if not m:
        raise BuildError(f"not a version: {version!r}")
    return tuple(int(x) for x in m[1].split("."))


def rules(path: Path = SETTINGS_FILE) -> list[dict]:
    rs = tomllib.loads(path.read_text())["rule"]
    for r in rs:
        if unknown := set(r) - KEYS:
            raise BuildError(f"{path}: unknown keys {sorted(unknown)} in a rule")
    return rs


def environment(version: str, path: Path = SETTINGS_FILE) -> dict[str, str]:
    """The compilers (CC CXX FC F77) with this version's options, and its
    configure answers."""
    v = key(version)
    opts: dict[str, list[str]] = {k: [] for k in COMPILERS}
    answers: dict[str, str] = {}
    for r in rules(path):
        if ("from" in r and v < key(r["from"])) or ("until" in r and v > key(r["until"])):
            continue
        for k in COMPILERS:
            if k in r:
                opts[k].append(r[k])
        for a in r.get("configure", []):
            name, _, value = a.partition("=")
            answers[name] = value
    cc, cxx, fc = (" ".join([COMPILERS[k], *opts[k]]) for k in ("cc", "cxx", "fc"))
    return {"CC": cc, "CXX": cxx, "FC": fc, "F77": fc, **answers}
