#!/bin/bash
# Find the newest release that does not link without -fcommon (GCC >= 10
# refuses globals defined in several files), by bisection over the releases
# on CRAN, with build/settings.toml as it is (no -fcommon rule yet). Assumes
# that once a release links, every newer one does. A build failing for any
# other reason stops the search. Progress in bisect-fcommon.log.
node=$(cd "$(dirname "$0")/.." && pwd)/node/speedr-node
work=${SPEEDR_WORK:-$HOME/speedr-work}
mapfile -t vs < <(for m in 3 4; do curl -fsSL "https://cloud.r-project.org/src/base/R-$m/"; done |
    grep -o -E 'R-[0-9]+\.[0-9]+\.[0-9]+\.tar\.gz' | sed 's/^R-//; s/\.tar\.gz$//' | sort -u -V)
log() { echo "$*" | tee -a "$work/bisect-fcommon.log"; }

links() {  # VERSION -> 0 if it builds, 1 if it fails to link for -fcommon's reason
    local v=$1
    if "$node" build "$v" > /dev/null 2>&1; then log "$v: builds"; return 0; fi
    if grep -q 'multiple definition of' "$work/build-$v.log"; then log "$v: multiple definitions"; return 1; fi
    log "$v: fails for another reason, see $work/build-$v.log"; exit 2
}

lo=0 hi=$(( ${#vs[@]} - 1 ))
links "${vs[$hi]}" || { log "even ${vs[$hi]} fails"; exit 2; }
if links "${vs[$lo]}"; then log "result: none (${vs[$lo]} links)"; exit 0; fi
while [ $(( hi - lo )) -gt 1 ]; do
    mid=$(( (lo + hi) / 2 ))
    if links "${vs[$mid]}"; then hi=$mid; else lo=$mid; fi
done
log "result: ${vs[$lo]} is the newest release that needs -fcommon (${vs[$hi]} links)"
