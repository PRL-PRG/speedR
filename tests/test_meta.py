import json
from pathlib import Path

from speedr import meta

EXAMPLE = json.loads((Path(__file__).parent / "data" / "meta-example.json").read_text())


def test_example_is_valid():
    assert meta.errors(EXAMPLE) == []


def test_missing_and_malformed_fields_are_reported():
    bad = {k: v for k, v in EXAMPLE.items() if k != "machine"} | {"kind": "nightly"}
    errs = meta.errors(bad)
    assert any("'machine' is a required property" in e for e in errs)
    assert any(e.startswith("kind:") for e in errs)


def test_unknown_top_level_keys_are_rejected():
    assert meta.errors(EXAMPLE | {"colour": "red"})
