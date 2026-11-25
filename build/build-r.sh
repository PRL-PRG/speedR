#!/bin/bash
# Runs inside the toolchain image: build GNU R from a CRAN tarball into PREFIX
# the way R builds by default (plain ./configure: -g -O2, internal BLAS and
# LAPACK, R as one binary, recommended packages). The compilers, with the
# settings node/speedr-node chose for this version (speedr build-env), come in the environment
# (CC CXX FC F77, configure cache answers), and the code layouts to install
# beside it (SPEEDR_LAYOUTS, build/layouts.sh).
#   build-r.sh TARBALL PREFIX build PACKAGE  build, install, add PACKAGE (a tarball)
#   build-r.sh TARBALL PREFIX configure      configure only; print config.h
set -euo pipefail
tarball=$1 prefix=$2 mode=${3:-build} package=${4:-}

# /build is a fixed path (a tmpfs), the same for every build
tar -C /build -xzf "$tarball"
cd /build/R-*

./configure --prefix="$prefix" > configure.log 2>&1 || { cat configure.log; exit 1; }
if [ "$mode" = configure ]; then
    # what configure decided, without lines that name the build itself
    grep -E '^#define|^/\* #undef' src/include/config.h | grep -v -E 'PACKAGE_|R_PRINTCMD'
    exit 0
fi
cat configure.log
make -j3
make install
# the suite's one extra package (the version of its time)
[ -z "$package" ] || "$prefix/bin/R" CMD INSTALL "$package" ||
    echo "speedr: ${package##*/} does not install on this R; its benchmarks are unsupported here"

# one-line expressions: R 3.0's Rscript cannot take a multi-line -e
"$prefix/bin/Rscript" --vanilla -e 'print(sessionInfo()); x <- sum(sapply(1:1e5, function(i) i %% 7)); stopifnot(x == 300000); cat("R runs\n")'
"$prefix/bin/Rscript" --vanilla -e 'for (p in c("MASS", "Matrix")) { library(p, character.only = TRUE); cat(p, format(packageVersion(p)), "loads\n") }'

# the code layouts (SPEEDR_LAYOUTS), relinked from this build tree
"$(dirname "$0")/layouts.sh" "$prefix"
