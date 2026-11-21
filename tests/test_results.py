import json
import shutil
from pathlib import Path

from speedr import results

EXAMPLE = Path(__file__).parent / "data" / "meta-example.json"


def make_checkout(root: Path) -> None:
    m = json.loads(EXAMPLE.read_text())
    (root / m["methodology"] / "index").mkdir(parents=True)
    for name, cols in results.INDEX_TABLES.items():
        (root / m["methodology"] / "index" / name).write_text(",".join(cols) + "\n")
    run = root.joinpath(*(m[k] for k in ("methodology", "impl", "machine", "version", "config",
                                        "run_id")))
    run.mkdir(parents=True)
    shutil.copy(EXAMPLE, run / "meta.json")


def test_valid_checkout(tmp_path):
    make_checkout(tmp_path)
    assert results.check(tmp_path) == []


def test_missing_table_and_column(tmp_path):
    make_checkout(tmp_path)
    (tmp_path / "0.1" / "index" / "events.csv").unlink()
    (tmp_path / "0.1" / "index" / "benchmarks.csv").write_text("id,suite\n")
    problems = results.check(tmp_path)
    assert any("events.csv: missing" in p for p in problems)
    assert any("benchmarks.csv: missing columns ['name', 'min_version']" in p for p in problems)


def test_misplaced_run(tmp_path):
    make_checkout(tmp_path)
    src = next((tmp_path / "0.1").glob("*/*/*/*/*"))
    dst = src.parent.parent / "lto" / src.name
    dst.parent.mkdir()
    src.rename(dst)
    assert any("directory does not match" in p for p in results.check(tmp_path))


def test_unknown_methodology(tmp_path):
    make_checkout(tmp_path)
    (tmp_path / "0.1").rename(tmp_path / "9.9")
    problems = results.check(tmp_path)
    assert any(p.endswith("9.9: unknown methodology version") for p in problems)
    assert any("directory does not match" in p for p in problems)
