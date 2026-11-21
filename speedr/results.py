"""The layout of speedR-results, and a check that a checkout follows it.

    <methodology>/<impl>/<machine>/<version>/<config>/<run_id>/   one per run:
        meta.json, samples.csv (per process), iterations.csv
    <methodology>/index/*.csv                                     what the dashboard reads

Results of different methodology versions are never compared, so each has its
own tree; <impl> is the R implementation (gnur, later others). The index
tables are derived from the runs by the ingest step (ingest.py). Columns listed
here are required; extra columns are allowed so the index can grow without
breaking older dashboards. Everything is stored uncompressed: git compresses
objects and deltas itself, and a compressed file defeats both.
"""

import csv
import json
from pathlib import Path

from . import meta, methodology

INDEX_TABLES: dict[str, list[str]] = {
    "runs.csv": ["run", "methodology", "machine", "impl", "version", "kind", "config", "date",
                 "svn_rev", "suspect", "sentinel_drift", "n_ok", "n_total"],
    "machines.csv": ["machine", "os", "arch", "cpu", "kernel", "toolchain", "profiler",
                     "profiles", "wake", "first_version"],
    "benchmarks.csv": ["id", "suite", "name", "min_version"],
    "events.csv": ["machine", "date", "event"],
    "unsupported.csv": ["machine", "impl", "version", "config", "benchmark", "reason"],
    # one row per benchmark process: median iteration time, GC time, peak RSS
    "samples.csv": ["run", "benchmark", "process", "time_ms", "gc_ms", "max_rss_mb"],
    # one row per benchmark and category: share of samples in execute()
    "profiles.csv": ["run", "benchmark", "category", "share"],
}


def _header(path: Path) -> list[str]:
    with open(path, newline="") as f:
        return next(csv.reader(f), [])


def check(root: Path) -> list[str]:
    """Every problem with a results checkout, as `path: message`."""
    problems = []
    known = {m.version for m in methodology.load_all()}
    for mdir in sorted(p for p in root.iterdir() if methodology.VERSION.match(p.name)):
        if mdir.name not in known:
            problems.append(f"{mdir}: unknown methodology version")
        for name, columns in INDEX_TABLES.items():
            path = mdir / "index" / name
            if not path.exists():
                problems.append(f"{path}: missing")
                continue
            missing = [c for c in columns if c not in _header(path)]
            if missing:
                problems.append(f"{path}: missing columns {missing}")
        for path in sorted(mdir.glob("*/*/*/*/*/meta.json")):
            m = json.loads(path.read_text())
            problems += [f"{path}: {e}" for e in meta.errors(m)]
            impl, machine, version, config, run = path.parent.relative_to(mdir).parts
            expected = (m.get("impl"), m.get("machine"), m.get("version"), m.get("config"),
                        m.get("run_id"), m.get("methodology"))
            if (impl, machine, version, config, run, mdir.name) != expected:
                problems.append(f"{path}: directory does not match "
                                "methodology/impl/machine/version/config/run_id")
    return problems
