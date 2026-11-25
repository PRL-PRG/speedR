import pytest

from speedr import configs, impls, machines


def test_repository_machines_are_valid():
    ms = machines.load_all()
    assert ms, "machines/ is empty"
    assert len({m.name for m in ms}) == len(ms)


def write(tmp_path, name, body):
    p = tmp_path / f"{name}.toml"
    p.write_text(body)
    return p


GOOD = '''name = "{name}"
os = "{os}"
arch = "x86_64"
runtime = "{runtime}"
profiler = "perf"
wake = "{wake}"
{extra}
'''


@pytest.mark.parametrize("fields, message", [
    (dict(os="macos", runtime="docker"), "docker runtime is Linux-only"),
    (dict(extra='[sentinel]\n"a/b" = -1'), "sentinel times must be positive"),
    (dict(wake="carrier-pigeon"), "wake must be one of"),
    (dict(extra='colour = "red"'), "unknown keys"),
])
def test_invalid_machines_are_rejected(tmp_path, fields, message):
    f = dict(name="box-1", os="linux", runtime="docker", wake="always-on", extra="") | fields
    with pytest.raises(machines.MachineError, match=message):
        machines.load(write(tmp_path, "box-1", GOOD.format(**f)))


def test_file_name_must_match(tmp_path):
    body = GOOD.format(name="box-2", os="linux", runtime="docker", wake="always-on", extra="")
    with pytest.raises(machines.MachineError, match="must match the file name"):
        machines.load(write(tmp_path, "box-1", body))


def test_repository_configs_are_valid():
    cs = configs.load_all()
    assert cs["default"].status == "active"


def test_configs_need_a_default(tmp_path):
    p = tmp_path / "configs.toml"
    p.write_text('[lto]\ndescription = "x"\n')
    with pytest.raises(configs.ConfigError, match="default"):
        configs.load_all(p)


def test_repository_impls_are_valid():
    reg = impls.load_all()
    assert reg["gnur"].reference and not reg["gnur"].base
    for i in reg.values():
        assert i.reference or (i.directory / "build.sh").is_file()


@pytest.mark.parametrize("toml, message", [
    ('name = "x1"\ntitle = "X"\ndescription = "d"\nrepo = "git@github.com:a/b"\nbase = "4.5.2"',
     "https://"),
    ('name = "x1"\ntitle = "X"\ndescription = "d"\nrepo = "https://a/b"\nbase = "devel"',
     "base must be a GNU R release"),
    ('name = "x1"\ntitle = "X"\ndescription = "d"\nrepo = "https://a/b"\nbase = "4.5.2"',
     "needs a build.sh"),
    ('name = "x1"\ntitle = "X"\ndescription = "d"\nflavour = "mint"', "unknown keys"),
])
def test_invalid_impls_are_rejected(tmp_path, toml, message):
    (tmp_path / "x1").mkdir()
    (tmp_path / "x1" / "impl.toml").write_text(toml)
    with pytest.raises(impls.ImplError, match=message):
        impls.load(tmp_path / "x1")
