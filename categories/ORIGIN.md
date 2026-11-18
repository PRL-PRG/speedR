# categories/

## `perf-rules.R`

Copied **unchanged** from the artifact of the VMIL26 paper *What do R
benchmarks measure?*: `analysis/perf-rules.R` at commit `8b42516` of
`fikovnik/VMIL26` (the file was last changed in `d69f08d`, 2026-08-29, by
Filip Křikava), sha256 `e1168de6b62309f76967be3006a1730d4a54dfb6466a4aed9c97ff8511f3ca29`.

It is the frame classification behind the paper's category profiles: the
rules that map a `perf` stack frame to a category of R's runtime, and the walk
that charges each sample to its innermost classified frame. Its own header says
the rules and the walk only mean anything together, so it is kept whole and
byte-identical, and not reimplemented elsewhere. A change to it belongs upstream
first, then here as a fresh copy (and a new `rules_version` in run metadata).

Licence: the VMIL26 repository is private. Its author, Filip Křikava, agreed
to publishing this file under the MIT licence.

## `categorize.R`

speedR's own (MIT). It applies `perf-rules.R` to the recordings of the
profile pass (`drivers/profile.py`, built on r-benchmarks' `rbench_perf.py`)
the same way VMIL26's `analysis/categories.Rmd` does, and writes the
per-recording category shares as a tidy CSV. It started in r-benchmarks
(PRL-PRG/r-benchmarks#3) and moved here when r-benchmarks kept to the suite
and its harnesses (PRL-PRG/r-benchmarks#4).
