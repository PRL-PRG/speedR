"""speedR: benchmark GNU R across releases, nightly builds, configurations and platforms."""

from pathlib import Path

__version__ = "0.1.0.dev0"

# The repository checkout this package runs from: machines/ and configs.toml
# live beside it, not inside the package, because they are edited as data.
REPO_ROOT = Path(__file__).resolve().parent.parent
