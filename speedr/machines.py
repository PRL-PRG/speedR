"""The machine registry: one TOML file per benchmark machine in machines/.

A machine is a concrete box, not a platform: speedups are only ever computed
between runs on the same machine. Secrets (MAC addresses, BMC credentials)
never go in these files; they name the Actions secret that holds them.
"""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import REPO_ROOT

MACHINES_DIR = REPO_ROOT / "machines"

OS = {"linux", "macos", "windows"}
ARCH = {"x86_64", "aarch64"}
# How the scheduler gets the machine running before a job (see docs/machines.md).
WAKE = {"wol", "ipmi", "relay", "always-on", "manual"}
RUNTIME = {"docker", "native"}
PROFILER = {"perf", "samply", "xctrace", "etw", "none"}
PROFILES = {"validated", "experimental", "none"}

NAME = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")
SECRET = re.compile(r"^[A-Z][A-Z0-9_]*$")


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
    wake_secret: str = ""           # Actions secret: MAC (wol/relay) or BMC host (ipmi)
    relay_host: str = ""
    notes: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def runner_labels(self) -> list[str]:
        """Labels the self-hosted runner on this machine registers with."""
        return ["self-hosted", "speedr", f"m-{self.name}", f"os-{self.os}",
                f"arch-{self.arch}"]

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
        if self.wake in {"wol", "ipmi", "relay"}:
            need(bool(SECRET.match(self.wake_secret)),
                 f"wake = {self.wake!r} needs wake_secret naming an Actions secret")
        if self.wake == "relay":
            need(bool(self.relay_host), "wake = 'relay' needs relay_host")
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
