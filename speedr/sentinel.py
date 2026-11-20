"""The sentinel: before every timing pass, a few short benchmarks on one fixed
build of R, compared with what the machine's cluster measured when it was
calibrated (machines/<name>.toml, `[sentinel]`: ms per benchmark).

Its deviation is the geometric mean of the benchmarks' time ratios to the
reference, minus 1. Within SUSPECT of the reference the run is fine; beyond it
the run is recorded as suspect; beyond FAIL the timing pass does not run.
"""

import math
import statistics

from . import ingest, machines

VERSION = "4.5.2"
# short and steady (iterations within 1% of each other), each stressing another
# part of R: calls and the byte-code interpreter, scalar floating point, vector
# arithmetic over memory, and a mix
BENCHMARKS = ["areWeFast/bounce", "shootout/nbody/nbody", "mathkernel/DoubleVecAdd-T1",
              "R-benchmark-25/Programmation/att3_1"]
RUN_DESIGN = {"runs": 2, "iterations": 8, "warmups": 3}
SUSPECT = 0.03
FAIL = 0.10


def plan() -> str:
    """Shell assignments for speedr-node: the R version, --include and run design."""
    include = "^(" + "|".join(BENCHMARKS) + ")$"
    return (f"version={VERSION} include='{include}' runs={RUN_DESIGN['runs']} "
            f"iterations={RUN_DESIGN['iterations']} warmups={RUN_DESIGN['warmups']}")


def times(report: dict) -> dict[str, float]:
    """ms per benchmark: the geometric mean of its processes' medians."""
    by: dict[str, list[float]] = {}
    for r in ingest.processes(report):
        if r["time_ms"]:
            by.setdefault(r["benchmark"], []).append(r["time_ms"])
    return {b: round(statistics.geometric_mean(v), 3) for b, v in by.items()}


def check(report: dict, machine: str) -> dict:
    """The sentinel's result (meta.json `sentinel`) for a report of its run."""
    t = times(report)
    ref = {b: float(v) for b, v in machines.load_all_by_name()[machine].sentinel.items()}
    out = {"version": VERSION, "times_ms": t, "reference_ms": ref, "deviation": None}
    if not ref:
        return out | {"status": "uncalibrated"}
    missing = sorted(set(ref) - set(t))
    if missing:
        return out | {"status": "failed", "error": f"no time for {missing}"}
    d = math.exp(statistics.fmean(math.log(t[b] / ref[b]) for b in ref)) - 1
    status = "failed" if abs(d) > FAIL else "suspect" if abs(d) > SUSPECT else "ok"
    return out | {"deviation": round(d, 5), "status": status}
