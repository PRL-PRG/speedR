"""The reduce step on a synthetic recording (tests/data/profile): two recordings
with nested suite and benchmark names, and a failed process. Each recording has
11 samples inside `execute()` (4 bcEval, 4 under Rf_allocVector3 -- one with a
libc leaf -- 2 R_gc_internal, 1 unresolved) and 2 in `setup()`."""

import csv
import shutil
import subprocess
from pathlib import Path

import pytest

from speedr import REPO_ROOT, profile

DATA = Path(__file__).parent / "data" / "profile"


def test_manifest_keys_come_from_the_report():
    rows, problems = profile.manifest(DATA / "report.json", DATA / "runs")
    assert [(r["suite"], r["benchmark"], r["run"]) for r in rows] == [
        ("shootout/nbody", "nbody", 1), ("SpeedTest", "prg/hmc/hmc1", 1)]
    assert all(Path(r["frames"]).is_file() and Path(r["stdout"]).is_file() for r in rows)
    assert problems == ["SpeedTest/prg/hmc/hmc1 run 2: failed: exit code 1"]


def r_with_packages() -> bool:
    if shutil.which("Rscript") is None:
        return False
    probe = ("for (p in c('dplyr','tidyr','readr','stringr','tibble')) "
             "library(p, character.only = TRUE)")
    return subprocess.run(["Rscript", "-e", probe], capture_output=True).returncode == 0


@pytest.mark.skipif(not r_with_packages(), reason="needs Rscript with dplyr, tidyr, readr, "
                    "stringr, tibble")
def test_categorize(tmp_path):
    rows, _ = profile.manifest(DATA / "report.json", DATA / "runs")
    profile.write_manifest(rows, tmp_path / "manifest.csv")
    subprocess.run(["Rscript", str(REPO_ROOT / "categories" / "categorize.R"),
                    "--causes", str(tmp_path / "causes.csv"),
                    str(tmp_path / "shares.csv"), str(tmp_path / "manifest.csv")],
                   check=True, capture_output=True)
    with open(tmp_path / "shares.csv") as f:
        shares = list(csv.DictReader(f))
    for key in [("shootout/nbody", "nbody"), ("SpeedTest", "prg/hmc/hmc1")]:
        got = {r["category"]: int(r["samples"]) for r in shares
               if (r["suite"], r["benchmark"]) == key and int(r["samples"])}
        assert got == {"interpreter": 4, "mem-alloc": 4, "mem-gc": 2, "unattributed": 1}
    with open(tmp_path / "causes.csv") as f:
        assert [r["cause"] for r in csv.DictReader(f)] == ["unresolved stack"] * 2
