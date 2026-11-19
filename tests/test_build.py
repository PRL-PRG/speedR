import pytest

from speedr import build


def env(version):
    return build.environment(version)


def test_current_release_gets_only_settings_that_change_no_code():
    e = env("4.6.2")
    assert e["CC"] == "gcc -fpermissive -std=gnu23"
    assert e["FC"] == e["F77"] == "gfortran -fallow-argument-mismatch"
    assert e["r_cv_have_curl728"] == "yes"


@pytest.mark.parametrize("version, std", [
    ("3.0.0", "gnu89"), ("3.2.0", "gnu89"), ("3.2.1", "gnu11"), ("3.5.0", "gnu11"),
    ("3.5.1", "gnu17"), ("4.5.0", "gnu17"), ("4.5.1", "gnu23"),
])
def test_the_c_dialect_of_the_time(version, std):
    assert f"-std={std}" in env(version)["CC"].split()


def test_fcommon_only_up_to_3_6_1():
    assert "-fcommon" in env("3.6.1")["CC"].split()
    assert "-fcommon" not in env("3.6.2")["CC"].split()


def test_a_devel_snapshot_gets_the_rules_of_its_release():
    assert env("4.7.0 Under development (unstable)") == env("4.7.0")
    assert env("4.6.2 Patched (2026-11-20 r90950)") == env("4.6.2")


def test_bad_input(tmp_path):
    with pytest.raises(build.BuildError, match="not a version"):
        env("devel")
    p = tmp_path / "settings.toml"
    p.write_text('[[rule]]\ncflags = "-O3"\n')
    with pytest.raises(build.BuildError, match="unknown keys"):
        build.environment("4.6.2", p)
