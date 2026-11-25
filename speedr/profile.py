"""The profile pass's recordings, listed for categories/categorize.R.

bench's PerfRecord writes each recording to `<dir>/<suite>/<benchmark>/<run>/`
(perf.data, perf-frames.csv) and the dir reporter puts the R process's stdout
next to it. Suites and benchmarks can both contain `/`, so the key cannot be
read back off the path; it comes from the JSON report instead.
"""

import csv
import json
from pathlib import Path

# How each benchmark is recorded: VMIL26's recipe, which categories/perf-rules.R
# was validated with (r-benchmarks' rbench.perf defaults are 1999 Hz, a 16 kB
# stack dump and 1 recording). drivers/profile.py takes them as its defaults.
PERF = {"freq": 999, "stack_size": 32768, "recordings": 5}

MANIFEST_COLUMNS = ["suite", "benchmark", "run", "frames", "stdout"]


def recording_dir(root: Path, execution: dict) -> Path:
    """Where bench put one execution's files (bench.report.dir.execution_dir,
    nested=False, for the variant-less benchmarks of r-benchmarks)."""
    path = root / execution["suite"] / execution["benchmark"]
    if execution.get("variant_label"):
        path /= execution["variant_label"].replace("/", "_")
    elif execution.get("variant", {}).get("pairs"):
        path /= ",".join(f"{k}={v}" for k, v in execution["variant"]["pairs"])
    return path / str(execution["run"])


def manifest(report: Path, root: Path) -> tuple[list[dict], list[str]]:
    """Rows for every recording that has a frame table, and a problem per
    execution that does not (a failed process, or perf that wrote nothing)."""
    rows, problems = [], []
    for e in json.loads(report.read_text())["executions"]:
        d = recording_dir(root, e)
        name = f"{e['suite']}/{e['benchmark']} run {e['run']}"
        if e.get("failure"):
            problems.append(f"{name}: failed: {e['failure']}")
        elif not (d / "perf-frames.csv").is_file():
            problems.append(f"{name}: no {d / 'perf-frames.csv'}")
        else:
            rows.append({"suite": e["suite"], "benchmark": e["benchmark"], "run": e["run"],
                         "frames": str(d / "perf-frames.csv"), "stdout": str(d / "stdout")})
    return rows, problems


def write_manifest(rows: list[dict], out: Path) -> None:
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, MANIFEST_COLUMNS)
        w.writeheader()
        w.writerows(rows)
