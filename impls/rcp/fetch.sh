#!/bin/bash
# impls/rcp/fetch.sh BASE_TARBALL, in a fresh checkout of r-compile-server
# with its submodules: what the patched R in R/ still needs from the network.
# Its recommended packages: R's tools/rsync-recommended would download them;
# here they come from the source tarball of the GNU R release it patches, so
# both builds have the same ones.
set -euo pipefail
base=$1
v=$(cut -d' ' -f1 R/VERSION)
b=$(basename "$base" .tar.gz)   # R-4.5.2: the tarball's top directory too
[ "$b" = "R-$v" ] || { echo "rcp's R is $v, its base is $b: fix base in impl.toml" >&2; exit 1; }
tar --warning=no-unknown-keyword -xzf "$base" -C R/src/library/Recommended --strip-components=4 \
    --wildcards "$b/src/library/Recommended/*.tar.gz"
R/tools/link-recommended
