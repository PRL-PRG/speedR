#!/bin/bash
# Runs inside the toolchain image: build GNU R from a CRAN tarball into PREFIX
# the way R builds by default (plain ./configure: -g -O2, internal BLAS and
# LAPACK, R as one binary, recommended packages). The compilers, with the
# settings node/speedr-node chose for this version (speedr build-env), come in the environment
# (CC CXX FC F77, configure cache answers), and the code layouts to install
# beside it (SPEEDR_LAYOUTS, see below).
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

# Code layouts: where the linker puts R's code moves the time of some
# benchmarks by up to 20% (branch prediction and instruction caches), and a
# change to R moves it. For each PAD in SPEEDR_LAYOUTS (bytes, 0 being R as
# built), R's objects are linked again behind PAD bytes of filler, the first
# object after the C runtime's, and installed in PREFIX/layout/PAD: hard links
# to PREFIX but for the R binary and the text files that name PREFIX. Linking
# again gives the binary that compiling with the filler gives, byte for byte.
# R's own flags for that link, as make reads them (Makeconf's line ends in a comment)
main_ldflags=$(make -s -C src/main --no-print-directory --eval 'speedr-ldflags: ; @echo $(MAIN_LDFLAGS)' speedr-ldflags)
# R_HOME inside the prefix: lib/R, or lib64/R (R 3.4 and older on x86-64)
home=$("$prefix/bin/R" RHOME); home=${home#"$prefix"/}
for pad in ${SPEEDR_LAYOUTS:-}; do
    [ "$pad" != 0 ] || continue
    printf '\t.text\n\t.globl speedr_layout_pad\nspeedr_layout_pad:\n\t.skip %d, 0xcc\n' "$pad" > "/build/pad$pad.s"
    rm -f src/main/R.bin
    make -C src/main R.bin MAIN_LDFLAGS="$main_ldflags /build/pad$pad.s"
    v=$prefix/layout/$pad; mkdir -p "$v"
    for d in "$prefix"/*; do [ "$d" = "$prefix/layout" ] || cp -al "$d" "$v/"; done
    rm "$v/$home/bin/exec/R"; install -m 755 src/main/R.bin "$v/$home/bin/exec/R"
    grep -rlIZ -F "$prefix" "$v" | xargs -0 -r sed -i "s#$prefix#$v#g"
    "$v/bin/R" --slave --vanilla -e "stopifnot(R.home() == '$v/$home'); cat('speedr: layout $pad runs\n')"
done
