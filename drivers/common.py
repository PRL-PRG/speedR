"""What speedR's two drivers share.

The drivers import r-benchmarks as the `rbench` package (`rbench.perf` for
the profile pass), pinned in speedR's pyproject.toml, and run in speedR's
environment (`uv run python drivers/timing.py ...`). They take r-benchmarks'
suite, harnesses, metrics and package hook as they are, and change only what
speedR needs differently:

- the R command line: `--slave` instead of `--no-echo`, so the same command
  runs R 3.x (which knows only `--slave`) and 4.x (which still accepts it), and
  `setarch -R` on Linux, so address-space randomisation is off for R alone;
- the run design (guidelines §3) and perf settings (§6) as defaults;
- the configuration's run-time environment from speedR's configs.toml;
- the benchmarks speedR leaves out (PRUNED);
- the timing pass also records CPU temperature and throttling (bench's Thermal).
"""

import platform
import sys
import tomllib
from pathlib import Path

CONFIGS_FILE = Path(__file__).resolve().parent.parent / "configs.toml"

# Benchmarks left out of the suite (methodology 0.5): noise beyond what a run
# can resolve, and nothing the rest of the suite does not exercise.
# mathkernel/MMM-T1: its time depends on where R's code is linked (one layout
# in eleven +20%), and its kernel, a scalar triple loop over 200x200 matrices,
# is also SpeedTest/prg/matmult/matmult_triplp's.
PRUNED = {"mathkernel/MMM-T1"}


def kept(b) -> bool:
    """bench filter: False for a benchmark in PRUNED."""
    return f"{b.suite}/{b.name}" not in PRUNED


def config_env(name: str) -> dict[str, str]:
    """The run-time environment configuration `name` sets (configs.toml `env`)."""
    with open(CONFIGS_FILE, "rb") as f:
        configs = tomllib.load(f)
    if name not in configs:
        sys.exit(f"unknown configuration {name!r}; see {CONFIGS_FILE}")
    return dict(configs[name].get("env", {}))


def r_command(R: Path, script: Path, args: list[str]) -> list[str]:
    cmd = [str(R), "--slave", "--vanilla", "-f", str(script), "--args", *args]
    if sys.platform == "linux":
        cmd = ["setarch", platform.machine(), "-R", *cmd]
    return cmd
