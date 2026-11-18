import pytest

from speedr import upstream


def test_pin_is_a_full_sha():
    p = upstream.pin()
    assert p.repo.startswith("https://github.com/PRL-PRG/r-benchmarks")
    assert len(p.commit) == 40 and int(p.commit, 16) >= 0


def test_bench_commit_from_uv_lock(tmp_path):
    (tmp_path / "uv.lock").write_text(
        'version = 1\n\n[[package]]\nname = "bench"\nversion = "0.1.0"\n'
        'source = { git = "https://github.com/PRL-PRG/bench.git#'
        '4639a83a664901d83db3637bab863374878e96ac" }\n')
    assert upstream.bench_commit(tmp_path) == "4639a83a664901d83db3637bab863374878e96ac"


def test_bench_commit_needs_a_git_lock(tmp_path):
    (tmp_path / "uv.lock").write_text(
        'version = 1\n\n[[package]]\nname = "bench"\nversion = "0.1.0"\n'
        'source = { registry = "https://pypi.org/simple" }\n')
    with pytest.raises(upstream.UpstreamError):
        upstream.bench_commit(tmp_path)
