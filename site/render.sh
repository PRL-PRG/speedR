#!/bin/sh
# Render the dashboard once per methodology version (../methodology/versions.csv)
# into _site/<version>/, each showing only the runs measured under it, and
# point _site/index.html at the newest. Extra arguments go to `quarto render`.
#
# SPEEDR_RESULTS_ROOT=<speedR-results checkout> renders its results: a version
# with an index there (<root>/<version>/index), and only those. Unset, every
# version renders the synthetic mock.
set -eu
cd "$(dirname "$0")"
versions=$(Rscript -e 'source("R/load.R"); cat(methodology_versions()$version)')
if [ -n "${SPEEDR_RESULTS_ROOT:-}" ]; then
    root=$(cd "$SPEEDR_RESULTS_ROOT" && pwd)
    with=""
    for v in $versions; do [ -d "$root/$v/index" ] && with="$with $v"; done
    versions=${with# }
    [ -n "$versions" ] || { echo "render.sh: no results in $root" >&2; exit 1; }
fi
export SPEEDR_RENDERED="$versions"   # the other versions the version bar links to
rm -rf _site
for v in $versions; do
    echo "render.sh: methodology $v"
    if [ -n "${SPEEDR_RESULTS_ROOT:-}" ]; then export SPEEDR_RESULTS="$root/$v/index"; fi
    SPEEDR_METHODOLOGY=$v quarto render --output-dir "_site/$v" "$@"
done
newest=${versions##* }
cat > _site/index.html <<HTML
<!doctype html>
<meta charset="utf-8">
<title>speedR</title>
<meta http-equiv="refresh" content="0; url=$newest/">
<link rel="canonical" href="$newest/">
<p><a href="$newest/">speedR, methodology $newest</a></p>
HTML
