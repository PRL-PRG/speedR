# speedR profile image (node/speedr-node image): the toolchain image, which the
# R builds run in, plus what the profile pass needs beside them: perf, the one
# the node's kernel comes with (PERF: the host's linux-perf version), and R
# with the packages categories/categorize.R reads the recordings with. A layer
# of its own, so that the toolchain image, and with it every build id, stays as
# it is.
FROM speedr-toolchain

ARG PERF
RUN test -n "$PERF" \
 && apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        "linux-perf=$PERF" \
        r-base-core r-cran-dplyr r-cran-tidyr r-cran-readr r-cran-stringr r-cran-tibble \
 && rm -rf /var/lib/apt/lists/*
