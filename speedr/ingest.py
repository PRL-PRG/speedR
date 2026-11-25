"""Ingest: turn the runs the nodes copy into the controller's spool into
speedR-results (layout: results.py).

    <spool>/<label>/<run_id>/
        run.env            the run: machine, node, methodology, host, suite, times
        speedr-build.env   the build: id, source, settings, toolchain
        timing.json        bench's report of the timing pass (its passes merged)
        sentinel.json      the sentinel before it (speedr sentinel)
        probe.json         the node's probe before the job (prlprg-bench prolog)

A run of another implementation than GNU R says so in run.env (impl, its
base release, the commit: impls/); it is kind `commit`, its version the
commit's first 12 hex digits.

A run of the profile pass (`pass=profile` in run.env) has, instead of the
timing pass and its sentinel

        profile.json       bench's report of the profile pass
        profile-shares.csv, profile-causes.csv   categories/categorize.R's output

`speedr-node` copies run.env last, so a run without it is still arriving; a
run whose pass failed (`exit` in run.env) is left in the spool.
Every new run becomes <methodology>/<impl>/<machine>/<version>/<config>/<run_id>/
(meta.json, and samples.csv, iterations.csv or profiles.csv, causes.csv); then
the index of each methodology that got new runs is rebuilt from all of its runs.
"""

import csv
import json
import math
import statistics
from pathlib import Path

from . import machines, meta, profile, results

SUITE_REPO = "https://github.com/PRL-PRG/r-benchmarks"
# speedr-build.env keys that describe the build; the rest are its settings
BUILD_KEYS = {"source", "version", "date", "id", "toolchain"}

SAMPLE_COLUMNS = ["benchmark", "process", "time_ms", "gc_ms", "max_rss_mb",
                  "cpu_temp_max", "cpu_throttle", "suspect"]
ITERATION_COLUMNS = ["benchmark", "process", "iteration", "warmup", "time_ms", "gc_ms"]
# a profile run: one row per recording and category, and the largest reasons
# a sample has no category (categorize.R's columns)
PROFILE_COLUMNS = ["benchmark", "recording", "category", "samples", "share"]
CAUSE_COLUMNS = ["benchmark", "recording", "cause", "leaf_sym", "leaf_dso", "samples", "share"]


def read_env(path: Path) -> dict[str, str]:
    """KEY=value lines (speedr-build.env, run.env); # comments ignored."""
    out = {}
    for line in path.read_text().splitlines():
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k] = v
    return out


def _benchmark(e: dict) -> str:
    b = f"{e['suite']}/{e['benchmark']}"
    return f"{b}[{e['variant_label']}]" if e.get("variant_label") else b


def _values(e: dict, metric: str, warmup: bool = False) -> list[float]:
    return [s["value"] for i in e["iterations"] if i["warmup"] == warmup
            for s in i["samples"] if s["metric"] == metric]


def processes(report: dict) -> list[dict]:
    """One row per R process of a bench report: the median of its measured
    iterations, and what the process itself recorded. A failed process has no
    times; `failure` says why."""
    rows = []
    for e in report["executions"]:
        ps = {s["metric"]: s for s in e["process_samples"]}
        times = _values(e, "runtime")
        ok = e["failure"] is None and times
        rss, temp, thr = ps.get("max_rss"), ps.get("cpu_temp_max"), ps.get("cpu_throttle")
        rows.append({
            "benchmark": _benchmark(e), "process": e["run"],
            "time_ms": statistics.median(times) if ok else None,
            "gc_ms": statistics.median(_values(e, "gc")) if ok and _values(e, "gc") else None,
            "max_rss_mb": round(rss["value"] / 1024, 1) if rss else None,
            "cpu_temp_max": temp["value"] if temp else None,
            "cpu_throttle": thr["value"] if thr else None,
            "suspect": any(s["extra"].get("suspect") for s in (temp, thr) if s),
            "failure": e["failure"],
        })
    return rows


def iterations(report: dict) -> list[dict]:
    rows = []
    for e in report["executions"]:
        for i in e["iterations"]:
            m = {s["metric"]: s["value"] for s in i["samples"]}
            rows.append({"benchmark": _benchmark(e), "process": e["run"],
                         "iteration": i["samples"][0]["iteration"] if i["samples"] else None,
                         "warmup": i["warmup"], "time_ms": m.get("runtime"),
                         "gc_ms": m.get("gc")})
    return rows


def merge_passes(reports: list[dict]) -> dict:
    """One report of a run timed in passes, one per code layout and each with
    one process per benchmark (speedr-node run): the k-th pass's executions
    become process k."""
    out = {**reports[0], "executions": [], "diagnostics": []}
    for k, r in enumerate(reports, 1):
        out["executions"] += [e | {"run": k} for e in r["executions"]]
        out["diagnostics"] += r.get("diagnostics", [])
    return out


def run_design(report: dict) -> dict:
    ex = report["executions"]
    full = max(ex, key=lambda e: len(e["iterations"]), default={"iterations": []})
    return {"runs": max((e["run"] for e in ex), default=1),
            "iterations": max(len(full["iterations"]), 1),
            "warmups": sum(i["warmup"] for i in full["iterations"])}


def _kind(label: str, run: dict) -> tuple[str, str, int | None]:
    """(version, kind, svn_rev) of a source label: 4.5.2, devel-r<rev>, or
    another implementation's <impl>-<commit>."""
    if run.get("impl", "gnur") != "gnur":
        return run["commit"][:12], "commit", None
    if label.startswith("devel-r"):
        return "devel", "devel", int(label.removeprefix("devel-r"))
    if label.startswith("patched"):
        raise ValueError(f"{label}: R-patched runs are not recorded yet")
    return label, "release", None


def _json(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def _pass(spool_run: Path) -> str:
    return read_env(spool_run / "run.env").get("pass", "timing")


def _reduced(spool_run: Path, name: str) -> list[dict]:
    """categorize.R's rows of a profile run, keyed like samples.csv."""
    return [r | {"benchmark": f"{r['suite']}/{r['benchmark']}", "recording": r["run"]}
            for r in read_csv(spool_run / name)]


def build_meta(spool_run: Path) -> dict:
    """meta.json of a spooled run (speedr/schema/meta.schema.json)."""
    run, build = read_env(spool_run / "run.env"), read_env(spool_run / "speedr-build.env")
    kind_of_pass = _pass(spool_run)
    report = json.loads((spool_run / f"{kind_of_pass}.json").read_text())
    version, kind, rev = _kind(run["label"], run)
    m = {
        "schema_version": 1, "run_id": run["run_id"], "methodology": run["methodology"],
        "machine": run["machine"], "impl": run.get("impl", "gnur"), "version": version,
        "kind": kind,
        "svn_rev": rev, "config": run.get("config", "default"),
        "build": {"id": build["id"], "source": run["source_sha256"],
                  "flags": {k: v for k, v in build.items() if k not in BUILD_KEYS},
                  # [:10]: a commit's date has a time too
                  "toolchain": build["toolchain"], "source_date": build["date"][:10]},
        "suite": {"repo": SUITE_REPO, "commit": run["rbench"], "bench_commit": run["bench"],
                  "speedr_commit": run["speedr"], "benchmarks": len({_benchmark(e) for e in
                                                                    report["executions"]})},
        "run_design": run_design(report) | {"cpuset": run["cpuset"], "aslr": False},
        "host": {"node": run["node"], "kernel": run["kernel"], "cmdline": run["cmdline"],
                 "os_release": run["os_release"], "boot_id": run["boot_id"],
                 "uptime_s": float(run["uptime_s"]), "slurm_job": run.get("job", ""),
                 "fingerprint": report.get("fingerprint", {})},
        "started": run["started"], "finished": run["finished"], "passes": [kind_of_pass],
    }
    if kind_of_pass == "profile":
        shares = _reduced(spool_run, "profile-shares.csv")
        unattributed = [float(r["share"]) for r in shares if r["category"] == "unattributed"]
        m["profile"] = {"profiler": "perf", "profiler_version": run["perf"],
                        "rules_version": run["rules"],
                        "frequency_hz": profile.PERF["freq"],
                        "call_graph": f"dwarf,{profile.PERF['stack_size']}",
                        "recordings": m["run_design"]["runs"],
                        "unattributed_share": statistics.fmean(unattributed or [0.0])}
    if "layouts" in run:
        m["run_design"]["layouts"] = [int(p) for p in run["layouts"].split()]
    if kind == "commit":
        m["base_gnur_version"] = run["base"]
        m["commit"] = {"repo": run["repo"], "ref": run["ref"], "sha": run["commit"],
                       "date": run["commit_date"]}
    if (probe := _json(spool_run / "probe.json")) is not None:
        m["host"]["probe"] = probe
    if (sentinel := _json(spool_run / "sentinel.json")) is not None:
        m["sentinel"] = sentinel
    return m


def _cell(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    return str(v)


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(columns)
        w.writerows([_cell(r.get(c)) for c in columns] for r in rows)


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def run_dir(root: Path, m: dict) -> Path:
    return root.joinpath(*(m[k] for k in ("methodology", "impl", "machine", "version", "config",
                                          "run_id")))


def ingest_run(spool_run: Path, root: Path) -> Path:
    m = build_meta(spool_run)
    if errs := meta.errors(m):
        raise ValueError(f"{spool_run}: invalid meta.json: {errs}")
    out = run_dir(root, m)
    out.mkdir(parents=True, exist_ok=True)
    if m["passes"] == ["profile"]:
        write_csv(out / "profiles.csv", PROFILE_COLUMNS, _reduced(spool_run, "profile-shares.csv"))
        write_csv(out / "causes.csv", CAUSE_COLUMNS, _reduced(spool_run, "profile-causes.csv"))
    else:
        report = json.loads((spool_run / "timing.json").read_text())
        write_csv(out / "samples.csv", SAMPLE_COLUMNS + ["failure"], processes(report))
        write_csv(out / "iterations.csv", ITERATION_COLUMNS, iterations(report))
    (out / "meta.json").write_text(json.dumps(m, indent=1) + "\n")   # last: marks it done
    return out


def _version_key(v: str) -> tuple:
    return tuple(int(x) for x in v.split(".")) if v != "devel" else (math.inf,)


def _first_line(s: str | None) -> str:
    return (s or "").strip().splitlines()[0][:200] if (s or "").strip() else ""


def rebuild_index(mdir: Path) -> None:
    """<methodology>/index/ from every run under it (columns: results.INDEX_TABLES)."""
    registry = {m.name: m for m in machines.load_all()}
    runs, samples, unsupported, first_ok, profiles = [], [], [], {}, []
    latest_host: dict[str, dict] = {}
    for path in sorted(mdir.glob("*/*/*/*/*/meta.json")):
        m = json.loads(path.read_text())
        date = m["build"].get("source_date", m["started"][:10])[:10]
        if m["passes"] == ["profile"]:
            profiles += profile_index(m, date, read_csv(path.parent / "profiles.csv"))
            continue
        rows = read_csv(path.parent / "samples.csv")
        thermal = sum(r["suspect"] == "TRUE" for r in rows)
        sentinel = m.get("sentinel", {})
        probe = m["host"].get("probe", {})
        ok = {r["benchmark"] for r in rows if r["time_ms"]}
        runs.append({
            "run": m["run_id"], "methodology": m["methodology"], "machine": m["machine"],
            "impl": m["impl"], "version": m["version"], "kind": m["kind"],
            "config": m["config"], "date": date,
            "svn_rev": m.get("svn_rev"),
            "suspect": thermal > 0 or "suspect" in (sentinel.get("status"), probe.get("status")),
            "sentinel_drift": sentinel.get("deviation"), "n_ok": len(ok),
            "n_total": len({r["benchmark"] for r in rows}), "node": m["host"]["node"],
            "started": m["started"], "sentinel_status": sentinel.get("status", ""),
            "probe_status": probe.get("status", ""), "thermal_suspect": thermal,
            "base": m.get("base_gnur_version") or "", "commit": m.get("commit", {}).get("sha", ""),
            "ref": m.get("commit", {}).get("ref", ""),
        })
        for r in rows:
            samples.append({"run": m["run_id"]} | r)
        for b in sorted({r["benchmark"] for r in rows} - ok):
            reason = next(r["failure"] for r in rows if r["benchmark"] == b)
            unsupported.append({"machine": m["machine"], "impl": m["impl"],
                                "version": m["version"], "config": m["config"],
                                "benchmark": b, "reason": _first_line(reason)})
        for b in ok if m["impl"] == "gnur" else ():   # the GNU R release it runs on from
            if b not in first_ok or _version_key(m["version"]) < _version_key(first_ok[b]):
                first_ok[b] = m["version"]
        if m["started"] >= latest_host.get(m["machine"], {}).get("started", ""):
            latest_host[m["machine"]] = m["host"] | {"started": m["started"],
                                                     "toolchain": m["build"]["toolchain"]}

    machine_rows = []
    for name, host in sorted(latest_host.items()):
        reg = registry.get(name)
        versions = [r["version"] for r in runs if r["machine"] == name and r["kind"] == "release"]
        machine_rows.append({
            "machine": name, "os": reg.os if reg else "", "arch": reg.arch if reg else "",
            "cpu": reg.cpu if reg else "",
            "kernel": f"Linux {host['kernel']} ({host['os_release']})",
            "toolchain": f"GCC 16 (gcc:16), R's own BLAS; image {host['toolchain'][:19]}…",
            "profiler": reg.profiler if reg else "", "profiles": reg.profiles if reg else "",
            "wake": reg.wake if reg else "",
            "first_version": min(versions, key=_version_key) if versions else "",
        })
    benchmarks = [{"id": b, "suite": b.split("/", 1)[0], "name": b.split("/", 1)[1],
                   "min_version": v} for b, v in sorted(first_ok.items())]

    idx = mdir / "index"
    idx.mkdir(exist_ok=True)
    tables = {
        "runs.csv": runs, "machines.csv": machine_rows, "benchmarks.csv": benchmarks,
        "events.csv": [], "unsupported.csv": unsupported, "profiles.csv": profiles,
        "samples.csv": samples,
    }
    extra = {"runs.csv": ["node", "started", "sentinel_status", "probe_status",
                          "thermal_suspect", "base", "commit", "ref"],
             "samples.csv": ["cpu_temp_max", "cpu_throttle", "suspect"],
             "profiles.csv": PROFILE_RUN_COLUMNS}
    for name, rows in tables.items():
        write_csv(idx / name, results.INDEX_TABLES[name] + extra.get(name, []), rows)


# a profile run is not a timing run (runs.csv): its rows say what they profiled
PROFILE_RUN_COLUMNS = ["machine", "version", "kind", "config", "date", "started", "recordings"]


def profile_index(m: dict, date: str, rows: list[dict]) -> list[dict]:
    """profiles.csv rows of a profile run: each category's share of a benchmark's
    execute() samples, the mean over its recordings (so each counts once)."""
    shares: dict[tuple[str, str], list[float]] = {}
    for r in rows:
        shares.setdefault((r["benchmark"], r["category"]), []).append(float(r["share"]))
    about = {"run": m["run_id"], "machine": m["machine"], "version": m["version"],
             "kind": m["kind"], "config": m["config"], "date": date, "started": m["started"]}
    return [about | {"benchmark": b, "category": c, "share": round(statistics.fmean(v), 6),
                     "recordings": len(v)} for (b, c), v in shares.items()]


def ingest(spool: Path, root: Path) -> list[Path]:
    """Ingest every finished run in `spool` that `root` does not have yet."""
    have = {p.parent.name for p in root.glob("*/*/*/*/*/*/meta.json")}
    new = []
    for run_env in sorted(spool.glob("*/*/run.env")):
        if run_env.parent.name not in have and read_env(run_env).get("exit") == "0":
            new.append(ingest_run(run_env.parent, root))
    for mdir in sorted({p.parents[4] for p in new}):
        rebuild_index(mdir)
    return new
