import pytest

from speedr import methodology


def test_repository_versions_are_valid():
    versions = methodology.load_all()
    assert versions[-1] == methodology.current()
    assert [m.key for m in versions] == sorted(m.key for m in versions)


def write(tmp_path, rows, texts=None):
    (tmp_path / "versions.csv").write_text("version,status,date,summary\n" + rows)
    for v in texts if texts is not None else []:
        (tmp_path / f"{v}.qmd").write_text("## text\n")
    return tmp_path


def test_newest_is_current_whatever_the_file_order(tmp_path):
    d = write(tmp_path, "0.10,draft,2027-01-01,b\n0.2,draft,2026-12-01,a\n", ["0.10", "0.2"])
    assert methodology.current(d).version == "0.10"


@pytest.mark.parametrize("rows, texts, message", [
    ("1,draft,2026-11-19,x\n", ["1"], "MAJOR.MINOR"),
    ("0.1,final,2026-11-19,x\n", ["0.1"], "status"),
    ("0.1,draft,2026-11-19,x\n", [], "no 0.1.qmd"),
    ("0.1,draft,2026-11-19,x\n0.1,draft,2026-11-20,y\n", ["0.1"], "twice"),
])
def test_bad_registries(tmp_path, rows, texts, message):
    with pytest.raises(methodology.MethodologyError, match=message):
        methodology.load_all(write(tmp_path, rows, texts))
