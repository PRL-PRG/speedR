import json
from pathlib import Path

import pytest

from speedr import ingest, machines, results, sentinel

RUN_ID = "20261120T010000Z-abc123"
SHA = "0123456789abcdef0123456789abcdef01234567"


def execution(suite, name, run, times, failure=None, temp=60.0, hot=False):
    its = [{"warmup": i == 0, "samples": [
        {"metric": "runtime", "value": t, "unit": "ms", "iteration": i, "extra": {}},
        {"metric": "gc", "value": t / 10, "unit": "ms", "iteration": i, "extra": {}}]}
        for i, t in enumerate(times)]
    extra = {"suspect": True} if hot else {}
    return {"suite": suite, "benchmark": name, "variant_label": "", "run": run,
            "failure": failure, "iterations": [] if failure else its,
            "process_samples": [] if failure else [
                {"metric": "max_rss", "value": 102400.0, "unit": "kB", "extra": {}},
                {"metric": "cpu_temp_max", "value": temp, "unit": "C", "extra": extra},
                {"metric": "cpu_throttle", "value": 0.0, "unit": "", "extra": extra}]}


REPORT = {"fingerprint": {"cpu_model": "x"}, "diagnostics": [], "executions": [
    execution("areWeFast", "bounce", 1, [900, 850, 860, 870]),
    execution("areWeFast", "bounce", 2, [905, 852, 858, 866], hot=True, temp=95.0),
    execution("shootout", "nbody", 1, [], failure="object 'x' not found"),
    execution("shootout", "nbody", 2, [], failure="object 'x' not found"),
]}


def spool_run(spool: Path, label="4.5.2", run_id=RUN_ID) -> Path:
    d = spool / label / run_id
    d.mkdir(parents=True)
    (d / "timing.json").write_text(json.dumps(REPORT))
    (d / "speedr-build.env").write_text(
        f"source={label}\nversion=4.5.2\ndate=2025-10-31\nid=7bb8db9dea5e1496\n"
        "package=clusterGeneration_1.3.8.tar.gz\nconfigure=R defaults\n"
        "toolchain=sha256:98654f0a44906f1a4584cbe9b936b726930e0d8e92053fff0048db038b38829d\n"
        "CC=gcc -fpermissive -std=gnu17\n")
    (d / "probe.json").write_text(json.dumps({"node": "n1", "status": "ok", "deviation": 0.01,
                                              "values": {"alu_ns": 1.6}, "reference": {}}))
    (d / "sentinel.json").write_text(json.dumps({
        "version": "4.5.2", "times_ms": {"areWeFast/bounce": 860.0},
        "reference_ms": {"areWeFast/bounce": 850.0}, "deviation": 0.0118, "status": "ok"}))
    (d / "run.env").write_text(
        f"run_id={run_id}\nlabel={label}\nmachine=kabylake\nnode=n1\njob=12\nconfig=default\n"
        "methodology=0.1\nstarted=2026-11-20T01:00:00Z\nfinished=2026-11-20T03:00:00Z\nexit=0\n"
        "kernel=7.0.0-43-generic\ncmdline=ro isolcpus=3\nos_release=Ubuntu 26.04 LTS\n"
        "boot_id=b\nuptime_s=300.5\ncpuset=3\nlayouts=0 1000\n"
        f"source_sha256={'a' * 64}\nspeedr={SHA}\nrbench={SHA}\nbench={SHA}\n")
    return d


def test_processes_take_the_median_of_measured_iterations():
    rows = ingest.processes(REPORT)
    assert rows[0]["time_ms"] == 860 and rows[0]["gc_ms"] == 86 and not rows[0]["suspect"]
    assert rows[1]["suspect"] and rows[1]["cpu_temp_max"] == 95.0
    assert rows[2]["time_ms"] is None and rows[2]["failure"] == "object 'x' not found"
    assert ingest.run_design(REPORT) == {"runs": 2, "iterations": 4, "warmups": 1}


def test_passes_become_processes():
    one = {"fingerprint": {"cpu_model": "x"}, "diagnostics": ["a"], "executions": [
        execution("areWeFast", "bounce", 1, [900, 850, 860, 870])]}
    two = {"fingerprint": {"cpu_model": "y"}, "diagnostics": [], "executions": [
        execution("areWeFast", "bounce", 1, [905, 852, 858, 866])]}
    merged = ingest.merge_passes([one, two])
    assert [e["run"] for e in merged["executions"]] == [1, 2]
    assert merged["fingerprint"] == {"cpu_model": "x"} and merged["diagnostics"] == ["a"]
    assert [r["time_ms"] for r in ingest.processes(merged)] == [860, 858]
    assert ingest.run_design(merged)["runs"] == 2
    assert one["executions"][0]["run"] == 1 and two["executions"][0]["run"] == 1   # untouched


def test_ingest_writes_runs_and_index(tmp_path):
    spool, root = tmp_path / "spool", tmp_path / "results"
    spool_run(spool)
    spool_run(spool, run_id="20261120T020000Z-def456").joinpath("run.env").unlink()  # arriving
    root.mkdir()

    new = ingest.ingest(spool, root)

    assert [p.name for p in new] == [RUN_ID]
    run = root / "0.1" / "gnur" / "kabylake" / "4.5.2" / "default" / RUN_ID
    m = json.loads((run / "meta.json").read_text())
    assert m["host"]["probe"]["status"] == "ok" and m["sentinel"]["status"] == "ok"
    assert m["build"]["flags"]["CC"] == "gcc -fpermissive -std=gnu17"
    assert m["run_design"]["layouts"] == [0, 1000]
    runs = ingest.read_csv(root / "0.1" / "index" / "runs.csv")
    assert runs[0]["run"] == RUN_ID and runs[0]["suspect"] == "TRUE"   # one hot process
    assert (runs[0]["n_ok"], runs[0]["n_total"]) == ("1", "2")
    unsupported = ingest.read_csv(root / "0.1" / "index" / "unsupported.csv")
    assert [u["benchmark"] for u in unsupported] == ["shootout/nbody"]
    assert results.check(root) == []
    assert ingest.ingest(spool, root) == []   # nothing new the second time


@pytest.fixture
def calibrated(monkeypatch):
    m = machines.Machine(name="kabylake", os="linux", arch="x86_64", wake="wol",
                         runtime="docker", profiler="perf", sentinel={"areWeFast/bounce": 860.0})
    monkeypatch.setattr(machines, "load_all_by_name", lambda: {"kabylake": m})


@pytest.mark.parametrize("scale, status", [(1.0, "ok"), (1.05, "suspect"), (0.8, "failed")])
def test_sentinel_status(calibrated, scale, status):
    report = {"executions": [execution("areWeFast", "bounce", 1,
                                       [t * scale for t in (900, 860, 860, 860)])]}
    assert sentinel.check(report, "kabylake")["status"] == status


def test_sentinel_without_its_benchmark_fails(calibrated):
    report = {"executions": [execution("areWeFast", "bounce", 1, [], failure="died")]}
    assert sentinel.check(report, "kabylake")["status"] == "failed"


def profile_run(spool: Path, run_id="20261125T010000Z-fed789") -> Path:
    """A profile run of the same build: bounce recorded twice, nbody once."""
    d = spool_run(spool, run_id=run_id)
    for f in ("timing.json", "sentinel.json"):
        (d / f).unlink()
    (d / "profile.json").write_text(json.dumps({"fingerprint": {}, "executions": [
        {"suite": "areWeFast", "benchmark": "bounce", "run": r, "failure": None,
         "iterations": [], "process_samples": []} for r in (1, 2)]}))
    head = "suite,benchmark,run,category,samples,kernel_samples,share,share_classified\n"
    (d / "profile-shares.csv").write_text(head + "".join(
        f"areWeFast,bounce,{r},{c},{n},10,{n / 10},\n"
        for r, cs in ((1, {"interpreter": 6, "mem-gc": 4, "unattributed": 0}),
                      (2, {"interpreter": 8, "mem-gc": 1, "unattributed": 1}))
        for c, n in cs.items()))
    (d / "profile-causes.csv").write_text(
        "suite,benchmark,run,cause,leaf_sym,leaf_dso,samples,share\n"
        "areWeFast,bounce,2,unresolved stack,[unknown],[unknown],1,0.1\n")
    env = (d / "run.env").read_text()
    (d / "run.env").write_text(env + "pass=profile\nperf=perf version 7.0.14\nrules=e1168de6b623\n")
    return d


def test_ingest_profile_run(tmp_path):
    spool, root = tmp_path / "spool", tmp_path / "results"
    spool_run(spool)
    profile_run(spool)
    root.mkdir()

    assert len(ingest.ingest(spool, root)) == 2
    idx = root / "0.1" / "index"
    assert [r["run"] for r in ingest.read_csv(idx / "runs.csv")] == [RUN_ID]   # timing only
    prof = {r["category"]: r for r in ingest.read_csv(idx / "profiles.csv")}
    assert prof["interpreter"]["share"] == "0.7" and prof["mem-gc"]["share"] == "0.25"
    assert prof["interpreter"]["version"] == "4.5.2" and prof["interpreter"]["recordings"] == "2"
    run = root / "0.1" / "gnur" / "kabylake" / "4.5.2" / "default" / "20261125T010000Z-fed789"
    m = json.loads((run / "meta.json").read_text())
    assert m["passes"] == ["profile"] and m["profile"]["recordings"] == 2
    assert m["profile"]["unattributed_share"] == pytest.approx(0.05)
    assert [r["cause"] for r in ingest.read_csv(run / "causes.csv")] == ["unresolved stack"]
    assert results.check(root) == []


def test_ingest_another_implementation(tmp_path):
    """A run of rcp at a commit: its own series, kind commit, compared with its base."""
    spool, root = tmp_path / "spool", tmp_path / "results"
    spool_run(spool)
    sha = "2683bf7642f68d579b2dc5fd15243aba3cc44513"
    d = spool_run(spool, label=f"rcp-{sha[:12]}", run_id="20261125T030000Z-0dd123")
    env = (d / "speedr-build.env").read_text()   # a commit's date, as speedr-node writes it
    (d / "speedr-build.env").write_text(
        env.replace("date=2025-10-31", "date=2026-11-24T10:00:00+01:00"))
    (d / "run.env").write_text((d / "run.env").read_text() + (
        f"impl=rcp\nbase=4.5.2\nrepo=https://github.com/PRL-PRG/r-compile-server\nref=main\n"
        f"commit={sha}\ncommit_date=2026-11-24T10:00:00+01:00\n"))
    root.mkdir()

    assert len(ingest.ingest(spool, root)) == 2
    run = root / "0.1" / "rcp" / "kabylake" / sha[:12] / "default" / "20261125T030000Z-0dd123"
    m = json.loads((run / "meta.json").read_text())
    assert (m["impl"], m["kind"], m["version"], m["base_gnur_version"]) == (
        "rcp", "commit", sha[:12], "4.5.2")
    assert m["commit"]["sha"] == sha and m["commit"]["ref"] == "main"
    assert m["build"]["source_date"] == "2026-11-24"
    runs = {r["impl"]: r for r in ingest.read_csv(root / "0.1" / "index" / "runs.csv")}
    assert runs["rcp"]["base"] == "4.5.2" and runs["rcp"]["commit"] == sha
    assert runs["gnur"]["base"] == "" and runs["gnur"]["kind"] == "release"
    bench = ingest.read_csv(root / "0.1" / "index" / "benchmarks.csv")
    assert {b["min_version"] for b in bench} == {"4.5.2"}   # GNU R's releases only
    assert results.check(root) == []
