# Benchmarking guidelines for the R interpreter (draft)

These guidelines describe how speedR measures R, so that its numbers can be
trusted, reproduced, and compared over time. They are a deliverable of the
project and will be refined as the pipeline is built; sections marked
*(to do)* are not settled yet.

## 1. What is measured

- **The suite.** The 118 programs of
  [r-benchmarks](https://github.com/PRL-PRG/r-benchmarks), in 8 suites, but
  those too noisy to resolve a change the dashboard flags and covered by the
  rest (`PRUNED` in `drivers/common.py`; under methodology 0.5,
  `mathkernel/MMM-T1`). Each
  benchmark defines `execute(size)` (timed) and optionally `setup()` and
  `doctor()` (untimed). A benchmark whose `doctor()` fails on a release is
  recorded as unsupported for that release, not dropped silently.
- **Implementations and versions.** GNU R releases from 3.0.0 and R-devel by
  SVN revision. The data model allows other implementations later.
- **Configurations.** `default` is a vanilla build (`-O2 -g`, OpenBLAS linked
  by name, single-threaded). Other configurations (no byte-code, LTO, GC
  variants, PGO, reference BLAS) differ from it in one documented way each
  (`configs.toml`).

## 2. Building R

- Builds come from **CRAN source tarballs** (releases) and the
  [r-devel/r-svn](https://github.com/r-devel/r-svn) mirror (R-devel), with
  `SVN-REVISION` written so R reports its revision.
- Builds run inside a **toolchain image pinned by digest** (Linux). The image
  digest is part of the build id, so a toolchain change is a new build.
- Recommended packages are not built. The few packages the suite needs are
  installed into each build's own library from a dated snapshot.
- Each build is checked: configure flags in `etc/Makeconf` match the
  configuration, and BLAS runs single-threaded.

## 3. Running benchmarks

- **Run design.** Separate R processes per benchmark (4 under methodology 0.5),
  each running 1 warm-up and 4 measured iterations (r-benchmarks' own default is 3 processes of 2 + 3;
  speedR's drivers set theirs). The process is the unit of replication: the spread
  between processes is larger than the spread within one.
- **Code layouts.** Each process of a run uses the build linked at another
  code layout (filler in front of R's code), because where R's code lies moves
  some benchmarks by up to 20%. A run is one pass over the suite per layout.
- **A pause before every iteration.** The harness idles 1 ms after its forced
  garbage collection, so no iteration inherits the branch-predictor state of
  the one before.
- **Order.** Benchmarks run in a shuffled order with a fixed seed.
- **Isolation.** r-benchmarks' sealed environment (no inherited shell
  environment, no user or site library, fixed locale, BLAS/OpenMP pinned to one
  thread), ASLR disabled for the R process (`setarch -R`), the container pinned
  to isolated cores (`--cpuset-cpus`, `--cpuset-mems`), and no network inside it.
  The packages a benchmark needs are installed before the session, so the
  package hook finds them and never reaches the network.
- **Command line.** `R --slave --vanilla -f harness.R`. r-benchmarks uses
  `--no-echo`, which R only knows from 4.0.0; `--slave` is the spelling every
  R since 3.0.0 accepts.
- **Two passes.** A timing pass without any profiler, then a separate profile
  pass. Profiling overhead never touches the timings.

## 4. Machines

- **Dedicated bare metal.** No other workload, no desktop, background services
  removed, kernel and firmware frozen between maintenance windows.
- **Denoising.** Frequency scaling, turbo boost, SMT and other noise sources are
  controlled with `bench denoise` and checked with `bench doctor` before every
  session; a failed check stops the session.
- **Sentinel.** Every session starts with a fixed benchmark on a fixed build. If
  it drifts more than 3% from the machine's recent median, the session is
  marked *suspect*: published, but excluded from change detection.
- **Change log.** Every change to a machine (kernel, firmware, toolchain image)
  is logged and shown on the dashboard, because it can move every number.

## 5. Statistics

- A benchmark's time on a run is the **geometric mean over processes** of the
  per-process median iteration time, with a 95% t-interval on the log scale
  (process as the unit) whose standard error has a 0.1% floor.
- A **speedup** is *time(A) / time(B)*, only between runs on the **same
  machine**.
- Suite-level numbers are **geometric means** over the benchmarks every compared
  run could execute, and the count is always shown.
- The **baseline** (1×) is the R version shipped in the newest Ubuntu LTS.
- **R-devel change detection** flags a benchmark that moves by more than 2%
  with an interval excluding no change, relative to the median of the previous
  7 good nights, and confirmed by the next 3 nights.

## 6. Profiles

- Each benchmark is recorded with `perf record --call-graph dwarf,32768` at
  999 Hz, 5 recordings, on the same vanilla build (no frame pointers, no
  `-fno-inline`: both change what is measured). These are the settings the
  classifier was validated with in VMIL'26; r-benchmarks' `rbench_perf.py`
  defaults to 1999 Hz, a 16 kB stack dump and 1 recording, so speedR's driver
  sets its own. The deeper stack dump matters: a truncated stack can lose the
  frame that would have classified the sample.
- Samples outside the benchmark's `execute()` window are dropped. Each remaining
  sample is charged to the **innermost** stack frame that the category rules
  of *What do R benchmarks measure?* (VMIL'26) recognise: interpreter, call,
  dispatch, lookup, primitives, mem-alloc, mem-duplicate, mem-gc, native-ffi,
  native-blas. The rest is reported as **unattributed**, never hidden.
- The classifier (`categories/perf-rules.R`) is speedR's copy of VMIL'26's,
  kept byte-identical; each profile records the rules version it was reduced with.
- A run whose unattributed share exceeds 5% fails the quality gate.
- Profiles from a profiler not yet validated against perf on Linux x86-64 are
  marked *experimental*.

## 7. Publishing

- Every run publishes its metadata (`meta.json`, schema in
  `speedr/schema/`), raw per-process samples, and reduced profiles to
  speedR-results under CC0, so any number on the dashboard can be recomputed.

## 8. Security

- Benchmark machines are self-hosted runners on public repositories. Workflows
  that reach them are never triggered by pull requests, and the machines hold
  no write credentials.

## To do

- Validation of the run design: sentinel spread across wake cycles, cold vs
  warm machine, same build two days apart.
- Guidance for package authors using the reusable workflow.
- Windows and macOS specifics.
