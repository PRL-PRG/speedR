import re
from datetime import UTC, datetime

from speedr.ids import build_id, run_id

ARGS = dict(impl="gnur", source="sha256:abc", config="default",
            flags={"CFLAGS": "-O2 -g"}, toolchain="sha256:img")


def test_build_id_is_stable_and_short():
    assert build_id(**ARGS) == build_id(**ARGS)
    assert re.fullmatch(r"[0-9a-f]{16}", build_id(**ARGS))


def test_build_id_ignores_flag_order():
    a = build_id(**{**ARGS, "flags": {"A": "1", "B": "2"}})
    b = build_id(**{**ARGS, "flags": {"B": "2", "A": "1"}})
    assert a == b


def test_build_id_changes_with_every_input():
    base = build_id(**ARGS)
    for key, value in [("impl", "rsh"), ("source", "r89000"), ("config", "lto"),
                       ("flags", {"CFLAGS": "-O3"}), ("toolchain", "sha256:other")]:
        assert build_id(**{**ARGS, key: value}) != base, key


def test_run_id_sorts_by_time():
    a = run_id(datetime(2026, 11, 11, 9, 30, tzinfo=UTC))
    b = run_id(datetime(2026, 11, 11, 9, 31, tzinfo=UTC))
    assert a.startswith("20261111T093000Z-") and a < b
