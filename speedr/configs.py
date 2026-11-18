"""Build configurations (configs.toml): the options a build of R is compiled
or run with. `default` is the reference every other config is compared to."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import REPO_ROOT

CONFIGS_FILE = REPO_ROOT / "configs.toml"
STATUS = {"active", "planned"}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Config:
    name: str
    description: str
    status: str = "planned"
    configure: list[str] = field(default_factory=list)   # extra ./configure arguments
    cflags: str = ""                                       # replaces the default -O2 -g
    env: dict[str, str] = field(default_factory=dict)      # set for every benchmark process
    platforms: list[str] = field(default_factory=list)     # empty: all; else "os" or "os/arch"


def load_all(path: Path = CONFIGS_FILE) -> dict[str, Config]:
    with path.open("rb") as f:
        data = tomllib.load(f)
    configs = {}
    for name, entry in data.items():
        unknown = set(entry) - set(Config.__dataclass_fields__)
        if unknown:
            raise ConfigError(f"{name}: unknown keys {sorted(unknown)}")
        c = Config(name=name, **entry)
        if c.status not in STATUS:
            raise ConfigError(f"{name}: status must be one of {sorted(STATUS)}")
        configs[name] = c
    if "default" not in configs or configs["default"].status != "active":
        raise ConfigError("configs.toml must define an active 'default' config")
    return configs
