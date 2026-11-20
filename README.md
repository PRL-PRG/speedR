# speedR

How fast is GNU R, and where does the time go? speedR benchmarks every R
release since 3.0.0 and every night of R-devel on dedicated machines, profiles
each benchmark to show *where* the interpreter spends its time, and publishes
the results as a static dashboard, in the spirit of
[speed.python.org](https://speed.python.org). The work is funded by an
[R Consortium](https://www.r-consortium.org) ISC grant, *Measuring R
Performance*.

> **Status: early development.** The first measurements (methodology 0.2,
> a draft) are on the dashboard, <https://prl-prg.github.io/speedR-results/>.
> See [Roadmap](#roadmap).

## What is in this repository

| path | what |
|---|---|
| [`site/`](site/) | the dashboard: Quarto + R, static ([README](site/README.md)) |
| [`speedr/`](speedr/) | the pipeline (Python): identifiers, machine registry, run metadata, the suite pin, build settings, the sentinel, the ingest into speedR-results |
| [`drivers/`](drivers/) | the timing and profile passes, built on r-benchmarks' `rbench` and `rbench.perf` |
| [`categories/`](categories/) | the perf frame classifier from VMIL'26 (`perf-rules.R`) and the step that turns recordings into category shares |
| [`machines/`](machines/) | one TOML file per machine: a set of identical boxes, with the sentinel's reference times |
| [`build/`](build/) | how R is built: the toolchain image (upstream GCC 16), the per-version settings ([`settings.toml`](build/settings.toml)) and the build script |
| [`node/`](node/) | running on the cluster: `speedr-node` (build; sentinel and timing pass, results to the controller), `speedr-submit` (queue it as a Slurm job) and, on the controller, `speedr-publish` (ingest and push to speedR-results) |
| [`configs.toml`](configs.toml) | build configurations: default, no-bytecode, LTO, GC variants, PGO, ... |
| [`methodology/`](methodology/) | methodology versions: every run records the one it was measured under ([rules](methodology/README.md)) |
| [`docs/`](docs/) | [benchmarking guidelines](docs/guidelines.md) (draft) |
| [`tests/`](tests/) | Python tests, including the workflow security rules |

Related repositories:

- [PRL-PRG/r-benchmarks](https://github.com/PRL-PRG/r-benchmarks): the
  benchmark suite (118 programs), its harnesses and drivers. speedR pins one
  commit of it (the `rbench` package, in `pyproject.toml`) and reuses its suite definitions, harnesses,
  metrics and package hook; speedR's drivers change only the R command line,
  the run design and the configuration's environment.
- [PRL-PRG/bench](https://github.com/PRL-PRG/bench): the benchmarking library
  r-benchmarks is built on. speedR does not pin it separately: it uses the
  commit r-benchmarks' `uv.lock` locks.
- [PRL-PRG/speedR-results](https://github.com/PRL-PRG/speedR-results): the
  results, under CC0 (branch `results`); every push there renders the
  dashboard.

## How it works

```
 speedr-submit (controller) ──► Slurm ──wake──► benchmark box (Slurm prolog: booted? probe)
                                                 │ build R (pinned image, cached)
                                                 │ sentinel (R 4.5.2, against the machine)
                                                 │ timing pass (r-benchmarks)
       controller spool ◄──── rsync ─────────────┘
        │ speedr-publish (cron): ingest, commit, push
        ▼
 speedR-results `results` ──► GitHub Actions renders the dashboard (Pages)
```

Speedups are only computed between runs **on the same machine** (a set of
identical boxes, checked against each other by the probe and the sentinel). The baseline
(1×) is the R version shipped in the newest Ubuntu LTS. The details are in
[the guidelines](docs/guidelines.md) and on the dashboard's Methodology page.

## Running it

Pipeline tooling (Python ≥ 3.12, [uv](https://docs.astral.sh/uv/)):

```sh
uv sync                      # create .venv with speedr and the dev tools
uv run speedr machines       # list and validate the machine registry
uv run speedr configs        # list and validate the build configurations
uv run speedr validate-meta path/to/meta.json
uv run pytest                # tests
uv run ruff check .          # lint
```

The two passes, on any R:

```sh
uv run speedr suite                  # the rbench and bench commits in use
uv run python drivers/timing.py --R /path/to/R --json timing.json
uv run python drivers/profile.py --R /path/to/R --json perf.json --dir perf/
uv run speedr profile-manifest perf.json perf/ manifest.csv
Rscript categories/categorize.R shares.csv manifest.csv  # needs dplyr, tidyr, readr, stringr, tibble
```

Both take `--config NAME` (run-time environment from `configs.toml`),
`--include`/`--exclude` and the rest of bench's options; `--help` lists them.

On the benchmark machines (a Slurm cluster; its setup is not part of this
repository), each node has this repository checked out as `~speedr/speedr`
(`uv sync` once) and the toolchain image built (`node/speedr-node image`).
From the controller:

```sh
speedr-submit build 4.5.2 devel   # one build job each (devel: today's R-devel snapshot)
speedr-submit run 4.5.2           # build if needed, then the sentinel and the timing pass
uv run speedr build-env 3.6.1     # the compilers and settings an R version is built with
```

The controller has the same checkout as `~speedr/speedr`, a checkout of
speedR-results' `results` branch as `~speedr/speedR-results` (a deploy key may
push to it) and runs `node/speedr-publish` from speedr's crontab.

Dashboard ([Quarto](https://quarto.org) ≥ 1.11 and R ≥ 4.3):

```sh
cd site
Rscript -e 'pak::local_install_deps()'   # or install the packages in site/DESCRIPTION
quarto preview                            # live preview
quarto render                             # static site in site/_site/
SPEEDR_RESULTS_ROOT=../../speedR-results ./render.sh       # real data, one site per methodology
```

## Roadmap

| phase | what | status |
|---|---|---|
| 1 | repositories, licences, contributor guide, CI | in progress |
| 2 | build layer: pinned images, GNU R builds 3.0.0 to R-devel | done |
| 3 | timing pass, results repository, scheduler, power management | done (methodology 0.2, draft) |
| 4 | dashboard on real data | first releases |
| 5 | profiles: perf pass, categorisation, quality gates | |
| 6 | nightly R-devel and change detection | |
| 7 | backfill of 3.x releases | |
| 8 | configurations: no-bytecode, LTO, GC variants, PGO | |
| 9 | more platforms: Linux arm64, macOS, Windows | |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Bugs and questions go to the
[issue tracker](https://github.com/PRL-PRG/speedR/issues).

## Licence

The code is under the [MIT licence](LICENSE). The results in speedR-results
are under CC0. Benchmark programs keep their original licences (see
r-benchmarks).
