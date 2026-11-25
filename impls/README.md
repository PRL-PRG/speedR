# Implementations

One directory per implementation of R. **GNU R** (`gnur/`) is the reference:
its releases and R-devel come from CRAN and build with `build/build-r.sh`.
Every other implementation is a git repository that speedR builds at a
commit and measures exactly as it measures GNU R: the same harness, run
design, code layouts, machines and statistics, under the same methodology.
Each commit is compared with the GNU R release the implementation is built on.

Nothing else in speedR names an implementation. The node script, Slurm jobs,
ingest, results tree (`<methodology>/<impl>/...`) and dashboard (the
Implementations page and Compare) read it from the run.

## Adding one

Make `impls/<name>/` (lowercase letters and digits) with:

| file | what it does |
|---|---|
| `impl.toml` | what it is (below) |
| `build.sh` | `build.sh SRC PREFIX PACKAGE`: builds the source tree `SRC` and installs it so that `PREFIX/bin/R` runs it, with the suite's extra package (`PACKAGE`, a tarball) installed. Runs in the image with **no network**, on the housekeeping CPUs. The compilers and settings of its base GNU R release are in the environment (`speedr build-env <base>`). If it is a GNU R build tree, it ends with `build/layouts.sh PREFIX`, run in that tree. |
| `fetch.sh` | optional, `fetch.sh BASE_TARBALL`: runs in a fresh checkout, with its submodules, while there is network. Whatever else the build needs goes in here, for example R's recommended packages, taken from the base release's tarball. |
| `Dockerfile` | optional: the image to build and run in, `FROM speedr-toolchain` plus what it needs. Pin nothing that changes GNU R's builds. |
| `profile.R` | optional: sourced by the harness before each benchmark. Its `rbench_prepare()`, if it defines one, runs after `setup()` and before the first iteration. This is where the implementation is switched on, for example by compiling `execute()`. Make it fail rather than let a benchmark run as plain R. |

```toml
# impls/<name>/impl.toml
name = "rcp"
title = "rcp"                    # how the site names it
description = "Copy-and-patch JIT compiler: an R package on a patched GNU R"
status = "experimental"          # or validated
repo = "https://github.com/PRL-PRG/r-compile-server"
base = "4.5.2"                   # the GNU R release it is built on: what it is compared with
track = "main"                   # optional: measured every night the branch moved
layouts = true                   # its R relinks at the code layouts, as GNU R does
```

`rcp/` is a complete example. Then:

```sh
uv run speedr impls                        # validates it
uv run pytest tests/test_registry.py
node/speedr-node image                     # on each node: builds its image
speedr-submit run <name>@<branch or commit>  # from the controller
```

Results land under `<methodology>/<name>/<machine>/<commit, 12 hex digits>/`,
of kind `commit`. The Implementations page shows them against the base
release, once that release has been measured on the same machine under the
same methodology. The methodology page says how each implementation is
switched on: describe yours there.

## What changes the build id

The commit, its `build.sh` and `fetch.sh` and the scripts around them
(`build/build-impl.sh`, `build/layouts.sh`), its image (so its Dockerfile),
its base release's settings, the extra package and the layouts. A change to any
of them builds it again. `profile.R` is not part of the build: it is recorded
with each run, by the speedR commit the run names.
