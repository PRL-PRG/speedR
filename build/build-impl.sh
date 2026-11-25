#!/bin/bash
# Runs inside an implementation's image (node/speedr-node): unpacks its source
# (a commit, fetched by speedr-node) on /build and builds it into PREFIX with
# impls/IMPL/build.sh. The compilers and settings of its base GNU R release
# come in the environment, as for GNU R (build/build-r.sh).
#   build-impl.sh IMPL TARBALL PREFIX PACKAGE
set -euo pipefail
impl=$1 tarball=$2 prefix=$3 package=$4
mkdir -p /build/src
tar -C /build/src -xzf "$tarball"
exec "$(cd "$(dirname "$0")/.." && pwd)/impls/$impl/build.sh" /build/src "$prefix" "$package"
