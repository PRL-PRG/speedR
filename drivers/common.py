"""What speedR's two drivers share.

The drivers run in r-benchmarks' own environment, not speedR's:

    RBENCH_ROOT=<checkout> uv run --project <checkout> python drivers/timing.py ...

so they import `rbench`, `rbench_perf` and `bench` from the pinned checkout
(`speedr fetch-suite`) and use nothing else outside the standard library. They
take r-benchmarks' suite, harnesses, metrics and package hook as they are, and
change only what speedR needs differently:

- the R command line: `--slave` instead of `--no-echo`, so the same command
  runs R 3.x (which knows only `--slave`) and 4.x (which still accepts it), and
  `setarch -R` on Linux, so address-space randomisation is off for R alone;
- the run design (guidelines §3) and perf settings (§6) as defaults;
- the configuration's run-time environment from speedR's configs.toml.
"""

import os
import platform
import sys
import tomllib
from pathlib import Path

CONFIGS_FILE = Path(__file__).resolve().parent.parent / "configs.toml"

RBENCH_ROOT = Path(os.environ.get("RBENCH_ROOT", "")).resolve()
if not (RBENCH_ROOT / "rbench.py").is_file():
    sys.exit("set RBENCH_ROOT to an r-benchmarks checkout (uv run speedr fetch-suite DIR)")
sys.path.insert(0, str(RBENCH_ROOT))


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
