#!/bin/bash
# Run in a GNU R build tree after `make install` into PREFIX (build/build-r.sh,
# and an implementation's build.sh that builds a GNU R): installs the build at
# the code layouts SPEEDR_LAYOUTS (node/speedr-node).
#   layouts.sh PREFIX
set -euo pipefail
prefix=$1

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
