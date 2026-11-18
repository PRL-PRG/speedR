"""The layout of speedR-results, and a check that a checkout follows it.

    runs/<machine>/<impl>/<version>/<config>/<run_id>/meta.json   one per run
    index/*.csv[.gz]                                              what the dashboard reads

The index tables are derived from runs/ by the ingest step. Columns listed
here are required; extra columns are allowed so the index can grow without
breaking older dashboards.
"""

import csv
import gzip
import json
from pathlib import Path

from . import meta

INDEX_TABLES: dict[str, list[str]] = {
    "runs.csv": ["run", "machine", "impl", "version", "kind", "config", "date", "svn_rev",
                 "suspect", "sentinel_drift", "n_ok", "n_total"],
    "machines.csv": ["machine", "os", "arch", "cpu", "kernel", "toolchain", "profiler",
                     "profiles", "wake", "first_version"],
    "benchmarks.csv": ["id", "suite", "name", "min_version"],
    "events.csv": ["machine", "date", "event"],
    "unsupported.csv": ["machine", "impl", "version", "config", "benchmark", "reason"],
    # one row per benchmark process: median iteration time, GC time, peak RSS
    "samples.csv.gz": ["run", "benchmark", "process", "time_ms", "gc_ms", "max_rss_mb"],
    # one row per benchmark and category: share of samples in execute()
    "profiles.csv.gz": ["run", "benchmark", "category", "share"],
}


def _header(path: Path) -> list[str]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", newline="") as f:
        return next(csv.reader(f), [])


def check(root: Path) -> list[str]:
    """Every problem with a results checkout, as `path: message`."""
    problems = []
    for name, columns in INDEX_TABLES.items():
        path = root / "index" / name
        if not path.exists():
            problems.append(f"{path}: missing")
            continue
        missing = [c for c in columns if c not in _header(path)]
        if missing:
            problems.append(f"{path}: missing columns {missing}")
    for path in sorted((root / "runs").glob("*/*/*/*/*/meta.json")):
        m = json.loads(path.read_text())
        problems += [f"{path}: {e}" for e in meta.errors(m)]
        machine, impl, version, config, run = path.parent.relative_to(root / "runs").parts
        expected = (m.get("machine"), m.get("impl"), m.get("version"), m.get("config"),
                    m.get("run_id"))
        if (machine, impl, version, config, run) != expected:
            problems.append(f"{path}: directory does not match machine/impl/version/config/run_id")
    return problems
