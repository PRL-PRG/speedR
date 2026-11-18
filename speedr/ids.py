"""Identifiers for builds and runs.

A *build* is one interpreter binary: an implementation at a source revision,
compiled with one configuration by one toolchain. Two builds with the same
inputs are interchangeable, so the id is a hash of exactly those inputs and a
machine can reuse a cached build whenever the id matches.

A *run* is one benchmarking session of a build on a machine. Runs of the same
build differ (time, machine state), so a run id is a timestamp plus a nonce.
"""

import hashlib
import json
import secrets
from datetime import UTC, datetime

BUILD_ID_LENGTH = 16


def build_id(impl: str, source: str, config: str, flags: dict[str, str], toolchain: str) -> str:
    """Stable hash of what determines a build's binary.

    `source` is the tarball sha256 for a release or `r<svn-rev>` for R-devel,
    `flags` the configure arguments and compiler flags the config expands to,
    and `toolchain` the build image digest (Linux) or toolchain manifest hash
    (macOS, Windows). The config *name* is included so that two configs that
    happen to expand to the same flags still get separate results.
    """
    payload = json.dumps(
        {"impl": impl, "source": source, "config": config, "flags": flags,
         "toolchain": toolchain},
        sort_keys=True, separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:BUILD_ID_LENGTH]


def run_id(now: datetime | None = None) -> str:
    """`20261111T093000Z-3f9a1c`: sorts by time; the nonce separates runs that
    start in the same second on different machines."""
    now = now or datetime.now(UTC)
    return f"{now.astimezone(UTC):%Y%m%dT%H%M%SZ}-{secrets.token_hex(3)}"
