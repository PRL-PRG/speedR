#!/usr/bin/env Rscript
#
# Category shares of `execute()` from the profile pass's perf recordings.
#
# Usage:
#   Rscript categories/categorize.R [--causes FILE] [--top N] OUT.csv MANIFEST.csv
#
# MANIFEST.csv lists the recordings, one row each (`speedr profile-manifest`
# writes it from the pass's JSON report):
#
#   suite, benchmark, run, frames, stdout
#
# `frames` is bench's `perf-frames.csv` and `stdout` the R process's output with
# the `MARK` lines `harness_instrument.R` printed. The key comes from the report,
# not from the directory layout, because suites and benchmarks can both be
# nested (`shootout/nbody` / `nbody_naive`, `SpeedTest` / `prg/hmc/hmc1`).
#
# For every recording this applies `perf-rules.R` -- the frame classification
# and the walk from the VMIL26 paper artifact, kept here unchanged -- exactly as
# its `categories.Rmd` does: frames are tagged with the harness phase their
# sample fell in, classified, each sample is charged to its innermost classified
# frame, and only samples inside the `execute` phase are counted.
#
# OUT.csv, one row per (recording, category), every category present (zero when
# none of its samples were seen) plus `unattributed`:
#
#   suite, benchmark, run             which recording
#   category                          a category of CATEGORIES, or `unattributed`
#   samples                           execute() samples charged to it
#   kernel_samples                    all execute() samples of the recording
#   share                             samples / kernel_samples; the categories
#                                     and `unattributed` sum to 1
#   share_classified                  samples / the classified kernel samples,
#                                     i.e. VMIL26's per-run `pct` / 100; NA for
#                                     `unattributed`
#
# --causes FILE writes, per recording, the N (default 10) largest reasons an
# execute() sample carries no category, from `unclassified_causes()`:
#
#   suite, benchmark, run, cause, leaf_sym, leaf_dso, samples, share
#
# with `share` again of all the recording's execute() samples.
#
# Runs on the analysis host, not on the R being measured: it needs R >= 4.1 and
# dplyr, tidyr, readr, stringr and tibble.

suppressPackageStartupMessages({
  library(dplyr)
  library(tidyr)
  library(readr)
  library(stringr)
  library(tibble)
})

# The categories `perf-rules.R` produces, in the order the paper reports them
# (VMIL26 `analysis/setup.R`, `CAT_GROUPS`). `other` is the interpreter's own
# outer frames (`main`, `Rf_mainloop`, ...) when nothing deeper matched.
CATEGORIES <- c(
  "interpreter", "call", "dispatch", "lookup",
  "primitives",
  "mem-alloc", "mem-duplicate", "mem-gc",
  "native-ffi", "native-blas",
  "other"
)
UNATTRIBUTED <- "unattributed"

here <- local({
  f <- sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))
  if (length(f) == 1L) dirname(normalizePath(f)) else "categories"
})
source(file.path(here, "perf-rules.R"))   # `rules` and the walk, unchanged

# As categories.Rmd checks it: a rule whose category is not reported would
# silently never show up.
stopifnot(all(rules$category %in% CATEGORIES))

usage <- function() {
  stop("usage: categorize.R [--causes FILE] [--top N] OUT.csv MANIFEST.csv",
       call. = FALSE)
}

parse_args <- function(args) {
  opts <- list(causes = NULL, top = 10L, out = NULL, manifest = NULL)
  i <- 1L
  while (i <= length(args)) {
    a <- args[[i]]
    if (a %in% c("--causes", "--top")) {
      if (i == length(args)) usage()
      v <- args[[i + 1L]]
      if (a == "--causes") opts$causes <- v else opts$top <- as.integer(v)
      i <- i + 2L
    } else if (startsWith(a, "--")) {
      usage()
    } else if (is.null(opts$out)) {
      opts$out <- a
      i <- i + 1L
    } else {
      if (!is.null(opts$manifest)) usage()
      opts$manifest <- a
      i <- i + 1L
    }
  }
  if (is.null(opts$out) || is.null(opts$manifest) || is.na(opts$top)) usage()
  opts
}

#' The recordings listed in a manifest, one row each.
read_manifest <- function(path) {
  m <- read_csv(path, col_types = cols(.default = col_character()))
  missing <- setdiff(c("suite", "benchmark", "run", "frames", "stdout"), names(m))
  if (length(missing)) stop(path, ": missing columns ", paste(missing, collapse = ", "),
                            call. = FALSE)
  arrange(m, suite, benchmark, run)
}

#' The execute() samples of one recording, one row each, with its category.
kernel_of <- function(rec) {
  marks <- read_perf_marks(rec$stdout)
  if (!any(marks$region == "execute")) {
    warning(rec$frames, ": no `MARK execute` line in ", rec$stdout,
            "; recording skipped", call. = FALSE)
    return(NULL)
  }
  frames <- read_perf_frames(rec$frames)
  if (!nrow(frames)) {
    warning(rec$frames, ": no frames; recording skipped", call. = FALSE)
    return(NULL)
  }
  frames <- frames |>
    add_marked_region(marks) |>
    classify_frames(rules)
  kernel <- sample_regions(frames) |>
    filter(!is.na(region), region == "execute")
  if (!nrow(kernel)) {
    warning(rec$frames, ": no samples inside execute(); recording skipped",
            call. = FALSE)
    return(NULL)
  }
  kernel
}

categorize <- function(rec, kernel) {
  key <- select(rec, suite, benchmark, run)
  counts <- kernel |>
    mutate(category = coalesce(category, UNATTRIBUTED)) |>
    count(category, name = "samples")
  out <- tibble(category = c(CATEGORIES, UNATTRIBUTED)) |>
    left_join(counts, by = "category") |>
    mutate(
      samples = coalesce(samples, 0L),
      kernel_samples = nrow(kernel),
      share = samples / kernel_samples,
      classified = sum(samples[category != UNATTRIBUTED]),
      share_classified = if_else(category == UNATTRIBUTED, NA_real_,
                                 samples / classified)
    ) |>
    select(-classified)
  bind_cols(key[rep(1L, nrow(out)), ], out)
}

causes_of <- function(rec, kernel, top) {
  key <- select(rec, suite, benchmark, run)
  causes <- unclassified_causes(kernel) |>
    arrange(desc(samples), cause, leaf_sym) |>
    slice_head(n = top) |>
    mutate(share = samples / nrow(kernel))
  if (!nrow(causes)) return(NULL)
  bind_cols(key[rep(1L, nrow(causes)), ], causes)
}

main <- function(args) {
  opts <- parse_args(args)
  recs <- read_manifest(opts$manifest)
  if (!nrow(recs)) stop(opts$manifest, ": no recordings", call. = FALSE)

  shares <- list()
  causes <- list()
  for (i in seq_len(nrow(recs))) {
    rec <- recs[i, ]
    kernel <- kernel_of(rec)
    if (is.null(kernel)) next
    shares[[length(shares) + 1L]] <- categorize(rec, kernel)
    causes[[length(causes) + 1L]] <- causes_of(rec, kernel, opts$top)
  }
  if (!length(shares)) stop("no recording had samples inside execute()", call. = FALSE)

  shares <- bind_rows(shares)
  stopifnot(all(abs(summarise(shares, t = sum(share),
                              .by = c(suite, benchmark, run))$t - 1) < 1e-9))
  write_csv(shares, opts$out, na = "")
  message(sprintf("%s: %d recording(s), %d row(s)", opts$out,
                  nrow(distinct(shares, suite, benchmark, run)),
                  nrow(shares)))

  if (!is.null(opts$causes)) {
    causes <- bind_rows(causes)
    if (!nrow(causes)) {
      causes <- tibble(suite = character(), benchmark = character(),
                       run = character(),
                       cause = character(), leaf_sym = character(),
                       leaf_dso = character(), samples = integer(),
                       share = double())
    }
    write_csv(causes, opts$causes, na = "")
    message(sprintf("%s: %d row(s)", opts$causes, nrow(causes)))
  }
}

if (sys.nframe() == 0L) main(commandArgs(trailingOnly = TRUE))
