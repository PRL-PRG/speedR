# Where the site's data comes from, and the one cache every page reads.
#
# SPEEDR_RESULTS=<checkout of speedR-results/index> renders real data; unset,
# the site renders the synthetic mock in data/mock (and says so on every page).

site_root <- function() {
  d <- Sys.getenv("QUARTO_PROJECT_DIR", "")
  if (nzchar(d)) return(normalizePath(d))
  d <- normalizePath(getwd())
  while (!file.exists(file.path(d, "_quarto.yml"))) {
    up <- dirname(d)
    if (up == d) stop("not inside the Quarto project")
    d <- up
  }
  d
}

is_mock <- function() !nzchar(Sys.getenv("SPEEDR_RESULTS", ""))

results_dir <- function() {
  if (is_mock()) file.path(site_root(), "data", "mock") else Sys.getenv("SPEEDR_RESULTS")
}

cache_path <- function() file.path(site_root(), "data", "_cache", "site.rds")

# read.csv opens and closes an unopened connection itself
read_gz <- function(path) utils::read.csv(gzfile(path), stringsAsFactors = FALSE)

#' Read the results index and derive everything the pages need. Called once by
#' the pre-render step; pages call site_data(), which reads the cache.
build_cache <- function() {
  source(file.path(site_root(), "R", "stats.R"), local = TRUE)
  dir <- results_dir()
  runs <- utils::read.csv(file.path(dir, "runs.csv"), stringsAsFactors = FALSE)
  runs$date <- as.Date(runs$date)
  machines <- utils::read.csv(file.path(dir, "machines.csv"), stringsAsFactors = FALSE)
  benchmarks <- utils::read.csv(file.path(dir, "benchmarks.csv"), stringsAsFactors = FALSE)
  events <- utils::read.csv(file.path(dir, "events.csv"), stringsAsFactors = FALSE)
  events$date <- as.Date(events$date)
  samples <- read_gz(file.path(dir, "samples.csv.gz"))
  profiles <- read_gz(file.path(dir, "profiles.csv.gz"))

  est <- estimate_runs(samples)

  # per-machine baselines and release timelines
  base <- lapply(machines$machine, function(m) baseline_run(runs, m))
  names(base) <- machines$machine
  rel_tl <- do.call(rbind, lapply(machines$machine, function(m) {
    r <- runs[runs$machine == m & runs$kind == "release" & runs$config == "default", ]
    timeline(est, r, base[[m]]$run)
  }))
  suite_tl <- do.call(rbind, lapply(machines$machine, function(m) {
    r <- runs[runs$machine == m & runs$kind == "release" & runs$config == "default", ]
    common <- common_benchmarks(est, c(r$run, base[[m]]$run))
    do.call(rbind, lapply(unique(benchmarks$suite), function(s) {
      sub <- intersect(common, benchmarks$id[benchmarks$suite == s])
      if (!length(sub)) return(NULL)
      t <- timeline(est, r, base[[m]]$run, sub)
      t$suite <- s
      t
    }))
  }))

  devel <- runs[runs$kind == "devel", ]
  latest_release <- function(m) {
    r <- runs[runs$machine == m & runs$kind == "release" & runs$config == "default", ]
    r[which.max(r$date), ]
  }
  devel_tl <- do.call(rbind, lapply(unique(devel$machine), function(m) {
    lr <- latest_release(m)
    timeline(est, devel[devel$machine == m, ], lr$run)
  }))
  changes <- devel_changes(est, devel)

  # profiles: category shares and group shares per (run, benchmark)
  cats <- read.csv(text = "category,group
interpreter,Evaluation
call,Evaluation
dispatch,Evaluation
lookup,Evaluation
primitives,Primitives
mem-alloc,Memory
mem-duplicate,Memory
mem-gc,Memory
native-ffi,Native code
native-blas,Native code
unattributed,Unattributed", stringsAsFactors = FALSE)
  profiles$group <- cats$group[match(profiles$category, cats$category)]

  saveRDS(list(
    generated = Sys.time(), mock = is_mock(),
    runs = runs, machines = machines, benchmarks = benchmarks, events = events,
    est = est, baselines = base, release_timeline = rel_tl, suite_timeline = suite_tl,
    devel_timeline = devel_tl, changes = changes, profiles = profiles
  ), cache_path())
}

site_data <- function() {
  if (!exists(".speedr_cache", envir = globalenv())) {
    assign(".speedr_cache", readRDS(cache_path()), envir = globalenv())
  }
  get(".speedr_cache", envir = globalenv())
}
