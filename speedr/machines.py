"""The machine registry: one TOML file per benchmark machine in machines/.

A machine is a set of identical boxes, one Slurm partition of the cluster
(`name` is the partition): the same hardware, firmware settings and system, so
their results are one series. Speedups are only ever computed between runs on
the same machine. `[sentinel]` holds the reference times the sentinel checks
every run's box against (speedr/sentinel.py).
"""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import REPO_ROOT

MACHINES_DIR = REPO_ROOT / "machines"

OS = {"linux", "macos", "windows"}
ARCH = {"x86_64", "aarch64"}
# how a sleeping box gets running before a job
WAKE = {"wol", "ipmi", "always-on", "manual"}
RUNTIME = {"docker", "native"}
PROFILER = {"perf", "samply", "xctrace", "etw", "none"}
PROFILES = {"validated", "experimental", "none"}

NAME = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")


class MachineError(ValueError):
    pass


@dataclass(frozen=True)
class Machine:
    name: str
    os: str
    arch: str
    wake: str
    runtime: str
    profiler: str
    profiles: str = "experimental"
    cpu: str = ""
    cores: str = ""                 # cpuset the benchmarks are pinned to, e.g. "2-7"
    numa_node: int | None = None
    track_devel: bool = False       # benchmark every R-devel night
    sentinel: dict = field(default_factory=dict)   # benchmark -> reference ms
    notes: str = ""
    extra: dict = field(default_factory=dict)

    def validate(self) -> None:
        def need(ok: bool, msg: str) -> None:
            if not ok:
                raise MachineError(f"{self.name}: {msg}")

        need(bool(NAME.match(self.name)), "name must be lowercase letters, digits and dashes")
        need(self.os in OS, f"os must be one of {sorted(OS)}")
        need(self.arch in ARCH, f"arch must be one of {sorted(ARCH)}")
        need(self.wake in WAKE, f"wake must be one of {sorted(WAKE)}")
        need(self.runtime in RUNTIME, f"runtime must be one of {sorted(RUNTIME)}")
        need(self.profiler in PROFILER, f"profiler must be one of {sorted(PROFILER)}")
        need(self.profiles in PROFILES, f"profiles must be one of {sorted(PROFILES)}")
        # Docker on macOS and Windows runs a Linux VM, which measures Linux.
        need(self.runtime != "docker" or self.os == "linux", "docker runtime is Linux-only")
        need(all(isinstance(v, (int, float)) and v > 0 for v in self.sentinel.values()),
             "sentinel times must be positive numbers (ms)")
        need(not self.extra, f"unknown keys: {sorted(self.extra)}")


def load(path: Path) -> Machine:
    with path.open("rb") as f:
        data = tomllib.load(f)
    known = {k: data.pop(k) for k in list(data) if k in Machine.__dataclass_fields__}
    m = Machine(**known, extra=data)
    if m.name != path.stem:
        raise MachineError(f"{path.name}: name {m.name!r} must match the file name")
    m.validate()
    return m


def load_all(directory: Path = MACHINES_DIR) -> list[Machine]:
    return [load(p) for p in sorted(directory.glob("*.toml"))]


def load_all_by_name(directory: Path = MACHINES_DIR) -> dict[str, Machine]:
    return {m.name: m for m in load_all(directory)}
