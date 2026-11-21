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
        "boot_id=b\nuptime_s=300.5\ncpuset=3\n"
        f"source_sha256={'a' * 64}\nspeedr={SHA}\nrbench={SHA}\nbench={SHA}\n")
    return d


def test_processes_take_the_median_of_measured_iterations():
    rows = ingest.processes(REPORT)
    assert rows[0]["time_ms"] == 860 and rows[0]["gc_ms"] == 86 and not rows[0]["suspect"]
    assert rows[1]["suspect"] and rows[1]["cpu_temp_max"] == 95.0
    assert rows[2]["time_ms"] is None and rows[2]["failure"] == "object 'x' not found"
    assert ingest.run_design(REPORT) == {"runs": 2, "iterations": 4, "warmups": 1}


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
