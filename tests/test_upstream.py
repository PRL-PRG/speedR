import pytest

from speedr import upstream


def lock(tmp_path, source):
    path = tmp_path / "uv.lock"
    path.write_text(f'version = 1\n\n[[package]]\nname = "bench"\nversion = "0.1.0"\n'
                    f'source = {source}\n')
    return path


def test_locked_commit(tmp_path):
    path = lock(tmp_path, '{ git = "https://github.com/PRL-PRG/bench.git?rev=4639a83a664901d83db'
                          '3637bab863374878e96ac#4639a83a664901d83db3637bab863374878e96ac" }')
    assert upstream.locked("bench", path) == "4639a83a664901d83db3637bab863374878e96ac"


def test_locked_needs_a_git_commit(tmp_path):
    path = lock(tmp_path, '{ registry = "https://pypi.org/simple" }')
    with pytest.raises(upstream.UpstreamError):
        upstream.locked("bench", path)
    with pytest.raises(upstream.UpstreamError):
        upstream.locked("rbench", path)


def test_environment_matches_the_lock():
    c = upstream.commits()
    assert set(c) == {"rbench", "bench"}
    assert all(len(sha) == 40 and int(sha, 16) >= 0 for sha in c.values())
