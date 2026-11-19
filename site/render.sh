#!/bin/sh
# Render the dashboard once per methodology version (../methodology/versions.csv)
# into _site/<version>/, each showing only the runs measured under it, and
# point _site/index.html at the newest. Extra arguments go to `quarto render`.
set -eu
cd "$(dirname "$0")"
versions=$(Rscript -e 'source("R/load.R"); cat(methodology_versions()$version)')
rm -rf _site
for v in $versions; do
    echo "render.sh: methodology $v"
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
