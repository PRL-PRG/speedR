"""The implementation registry: one directory per R implementation in impls/.

GNU R is the reference: its releases and R-devel come from CRAN and build
with build/build-r.sh (impls/gnur says only what it is). Every other
implementation is a git repository that speedR builds at a commit, beside
GNU R and measured the same way, and compares with the GNU R release it is
built from (`base`). Its directory holds

    impl.toml    what it is: the fields of Impl below
    build.sh     SRC PREFIX PACKAGE: build the source tree SRC, install it in
                 PREFIX (PREFIX/bin/R runs it) with the suite's extra PACKAGE;
                 runs in the image, with no network, after build/layouts.sh's
                 rules if `layouts` (node/speedr-node)
    fetch.sh     optional, BASE_TARBALL: completes a fresh checkout while there
                 is network (submodules are already there)
    Dockerfile   optional: the image to build in, on top of speedr-toolchain
    profile.R    optional: sourced by the harness before the benchmark (its
                 rbench_prepare() runs after setup()): what switches the
                 implementation on for the measured iterations
"""

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import REPO_ROOT

IMPLS_DIR = REPO_ROOT / "impls"
REFERENCE = "gnur"
STATUS = {"validated", "experimental", "planned"}
NAME = re.compile(r"^[a-z][a-z0-9]*$")   # no dashes: a source label is <name>-<commit>
RELEASE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


class ImplError(ValueError):
    pass


@dataclass(frozen=True)
class Impl:
    name: str
    title: str
    description: str
    status: str = "experimental"
    repo: str = ""          # git repository (empty: the reference, GNU R)
    base: str = ""          # the GNU R release it is built from, and compared with
    track: str = ""         # branch measured every night it moved (empty: on request only)
    layouts: bool = False   # its R binary relinks at speedR's code layouts like GNU R's
    extra: dict = field(default_factory=dict)

    @property
    def directory(self) -> Path:
        return IMPLS_DIR / self.name

    @property
    def reference(self) -> bool:
        return self.name == REFERENCE

    def validate(self) -> None:
        def need(ok: bool, msg: str) -> None:
            if not ok:
                raise ImplError(f"{self.name}: {msg}")

        need(bool(NAME.match(self.name)), "name must be lowercase letters and digits")
        need(self.status in STATUS, f"status must be one of {sorted(STATUS)}")
        need(not self.extra, f"unknown keys: {sorted(self.extra)}")
        if self.reference:
            need(not (self.repo or self.base or self.track), "GNU R has no repo, base or track")
            return
        need(self.repo.startswith("https://"), "repo must be an https:// git URL")
        need(bool(RELEASE.match(self.base)), "base must be a GNU R release, e.g. 4.5.2")
        need((self.directory / "build.sh").is_file(), "needs a build.sh")

    def shell(self) -> str:
        """Its settings as shell assignments, impl_<field> (node/speedr-node evals them)."""
        has = {f: (self.directory / f).is_file() for f in ("fetch.sh", "Dockerfile", "profile.R")}
        vals = {"repo": self.repo, "base": self.base, "track": self.track,
                "layouts": int(self.layouts), "fetch": int(has["fetch.sh"]),
                "dockerfile": int(has["Dockerfile"]), "profile": int(has["profile.R"])}
        return "\n".join(f"impl_{k}='{v}'" for k, v in vals.items())


def load(directory: Path) -> Impl:
    with (directory / "impl.toml").open("rb") as f:
        data = tomllib.load(f)
    known = {k: data.pop(k) for k in list(data) if k in Impl.__dataclass_fields__}
    i = Impl(**known, extra=data)
    if i.name != directory.name:
        raise ImplError(f"{directory}: name {i.name!r} must match the directory")
    i.validate()
    return i


def load_all(directory: Path = IMPLS_DIR) -> dict[str, Impl]:
    out = {p.parent.name: load(p.parent) for p in sorted(directory.glob("*/impl.toml"))}
    if REFERENCE not in out:
        raise ImplError(f"{directory}: no {REFERENCE}/impl.toml")
    return out
