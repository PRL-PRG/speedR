#!/bin/bash
# impls/rcp/build.sh SRC PREFIX PACKAGE, in the rcp image (node/speedr-node):
# rcp's patched GNU R, built as speedR builds GNU R (plain ./configure, with
# the compilers and settings of its base release, which come in the
# environment), plus -DRCP, the variant the rcp package links against
# (tools/build-gnur.sh with RCP=1 adds the same); then the suite's extra
# package, the rcp package as client/rcp's Makefile installs it, and the code
# layouts.
set -euo pipefail
src=$1 prefix=$2 package=$3
here=$(cd "$(dirname "$0")" && pwd)

cd "$src/R"
# a git checkout rather than a release tarball: what R's build expects of one
# (as tools/build-gnur.sh does)
[ -f doc/FAQ ] || touch doc/FAQ
if [ ! -f SVN-REVISION ]; then
    printf 'Revision: 1\nLast Changed Date: %s\n' "${SPEEDR_SOURCE_DATE:-2000-01-01}" > SVN-REVISION
    rm -f non-tarball
fi
# R's configure takes -I/usr/local/include when CPPFLAGS is not set: keep that
CPPFLAGS="${CPPFLAGS:--I/usr/local/include} -DRCP" ./configure --prefix="$prefix" > configure.log 2>&1 ||
    { cat configure.log; exit 1; }
cat configure.log
make -j3
make install
"$prefix/bin/R" CMD INSTALL "$package"
# rcp's build tools (the stencil extractor) are C++ from GCC 16 and need its
# libstdc++, in /usr/local/lib64; R's etc/ldpaths would put Ubuntu's older one
# first for everything R runs, R CMD INSTALL's compilers included
home=$("$prefix/bin/R" RHOME)
# Its helper library is linked into rcp.so, but nothing asks for -fPIC: Ubuntu's
# GCC makes position-independent code by default, upstream GCC does not. So it
# is built first, with -fPIC added to its flags (rcp's makefiles append theirs).
CFLAGS=-fPIC R_HOME=$home make -C "$src/client/rcp/rcp/src/shared"
R_LD_LIBRARY_PATH=/usr/local/lib64:$home/lib:/usr/local/lib:/usr/lib/x86_64-linux-gnu \
    make -C "$src/client/rcp/rcp" install R_HOME="$home"

"$prefix/bin/Rscript" --vanilla -e 'print(sessionInfo()); x <- sum(sapply(1:1e5, function(i) i %% 7)); stopifnot(x == 300000); cat("R runs\n")'
"$prefix/bin/Rscript" --vanilla -e 'suppressPackageStartupMessages(library(rcp)); f <- rcp_cmpfun(function(n) { s <- 0; for (i in 1:n) s <- s + i; s }, list(optimize = 3L, cache = FALSE)); stopifnot(rcp_is_compiled(f), f(100) == 5050); cat("rcp compiles\n")'
"$here/../../build/layouts.sh" "$prefix"
