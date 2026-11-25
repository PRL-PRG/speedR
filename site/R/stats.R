# Statistics behind every number on the site. Pure functions over plain data
# frames, so they are testable without rendering anything.
#
# Unit of replication is the R process (an "invocation"): each benchmark is run
# in several processes, and each process reports one value (the median of its
# measured iterations). A benchmark's estimate is the geometric mean over
# processes, with a t-interval on the log scale whose standard error has a floor
# (FLOOR): what a run carries beyond its processes' spread.
#
# NOTE (mockup): the plan calls for a hierarchical bootstrap (processes, then
# iterations). The analytic interval here has the same interface; swap the body
# of `estimate_runs()` once iteration-level samples exist.

Z <- 1.96                  # suite-level intervals: means over many benchmarks
FLOOR <- 0.001             # added (in quadrature) to every run's log standard error
CHANGE_THRESHOLD <- 0.02   # |speedup - 1| above this AND a CI excluding 1 => flagged

#' The 97.5% t quantile for a 95% interval with `df` degrees of freedom: n - 1
#' for one run of n processes, n_a + n_b - 2 for the comparison of two.
tq <- function(df) stats::qt(0.975, pmax(df, 1))

#' One row per (run, benchmark): log-mean, its standard error, and friends.
estimate_runs <- function(samples) {
  ok <- samples[!is.na(samples$time_ms), ]
  key <- paste(ok$run, ok$benchmark, sep = "\r")
  lt <- log(ok$time_ms)
  m <- tapply(lt, key, mean)
  s <- tapply(lt, key, stats::sd)
  n <- tapply(lt, key, length)
  gc <- tapply(ok$gc_ms, key, stats::median)
  rss <- tapply(ok$max_rss_mb, key, stats::median)
  parts <- do.call(rbind, strsplit(names(m), "\r", fixed = TRUE))
  data.frame(
    run = type.convert(parts[, 1], as.is = TRUE), benchmark = parts[, 2],
    log_mean = unname(m), log_se = unname(sqrt(s^2 / n + FLOOR^2)), n = unname(n),
    est_ms = unname(exp(m)), gc_ms = unname(gc), max_rss_mb = unname(rss),
    stringsAsFactors = FALSE
  )
}

#' Speedup of `new` over `base` per benchmark (base time / new time), with CI.
#' `base` and `new` are rows of estimate_runs() for one run each.
speedups <- function(base, new) {
  j <- merge(base[, c("benchmark", "log_mean", "log_se", "n")],
             new[, c("benchmark", "log_mean", "log_se", "n")],
             by = "benchmark", suffixes = c("_base", "_new"))
  d <- j$log_mean_base - j$log_mean_new
  se <- sqrt(j$log_se_base^2 + j$log_se_new^2)
  q <- tq(j$n_base + j$n_new - 2)
  data.frame(benchmark = j$benchmark, log_speedup = d, log_se = se,
             speedup = exp(d), lo = exp(d - q * se), hi = exp(d + q * se),
             significant = abs(d) > q * se & abs(exp(d) - 1) > CHANGE_THRESHOLD,
             stringsAsFactors = FALSE)
}

#' Geometric mean of per-benchmark speedups over the given subset.
geomean_speedup <- function(sp, subset = NULL) {
  if (!is.null(subset)) sp <- sp[sp$benchmark %in% subset, ]
  n <- nrow(sp)
  if (n == 0) return(data.frame(speedup = NA, lo = NA, hi = NA, n = 0))
  m <- mean(sp$log_speedup)
  se <- sqrt(sum(sp$log_se^2)) / n
  data.frame(speedup = exp(m), lo = exp(m - Z * se), hi = exp(m + Z * se), n = n)
}

#' Benchmarks present in every one of the given runs.
common_benchmarks <- function(est, runs) {
  sets <- split(est$benchmark, est$run)[as.character(runs)]
  Reduce(intersect, sets)
}

#' For each run of a machine: geomean speedup over that machine's baseline run,
#' over the benchmarks common to all the runs in `runs`.
timeline <- function(est, runs_meta, baseline_run, subset = NULL) {
  base <- est[est$run == baseline_run, ]
  ids <- runs_meta$run
  if (is.null(subset)) subset <- common_benchmarks(est, c(ids, baseline_run))
  out <- lapply(ids, function(r) {
    g <- geomean_speedup(speedups(base, est[est$run == r, ]), subset)
    cbind(runs_meta[runs_meta$run == r, ], g)
  })
  do.call(rbind, out)
}

#' R as shipped in each Ubuntu LTS release (r-base in the release pocket).
#' The newest one is the baseline: it is the R most Linux users get without
#' adding CRAN's apt repository. The pre-render step (R/ubuntu.R) adds new LTS
#' releases to data/ubuntu-lts.csv; this copy seeds that file.
UBUNTU_LTS_FALLBACK <- data.frame(
  ubuntu = c("14.04", "16.04", "18.04", "20.04", "22.04", "24.04", "26.04"),
  r      = c("3.0.2", "3.2.3", "3.4.4", "3.6.3", "4.1.2", "4.3.3", "4.5.2"),
  stringsAsFactors = FALSE)
UBUNTU_LTS_FILE <- file.path(Sys.getenv("QUARTO_PROJECT_DIR", "."), "data", "ubuntu-lts.csv")
UBUNTU_LTS <- if (file.exists(UBUNTU_LTS_FILE)) {
  utils::read.csv(UBUNTU_LTS_FILE, stringsAsFactors = FALSE, colClasses = "character")
} else UBUNTU_LTS_FALLBACK
BASELINE_VERSION <- UBUNTU_LTS$r[nrow(UBUNTU_LTS)]

is_lts <- function(version) version %in% UBUNTU_LTS$r

#' "Ubuntu 24.04" for an LTS R version, NA otherwise.
lts_name <- function(version) {
  u <- UBUNTU_LTS$ubuntu[match(version, UBUNTU_LTS$r)]
  ifelse(is.na(u), NA_character_, paste("Ubuntu", u))
}

#' The baseline run for a machine: the requested release if the machine has it,
#' else the machine's earliest release.
baseline_run <- function(runs, machine, version = BASELINE_VERSION, config = "default") {
  r <- runs[runs$machine == machine & runs$kind == "release" & runs$config == config, ]
  hit <- r$run[r$version == version]
  if (length(hit)) return(list(run = hit[1], version = version))
  first <- r[order(r$date), ][1, ]
  list(run = first$run, version = first$version)
}

#' One row per flagged R-devel night: how many benchmarks moved which way,
#' the largest move, and whether later nights have confirmed it yet.
devel_nights <- function(changes) {
  if (!nrow(changes)) return(data.frame())
  by_night <- split(changes, changes$run)
  out <- do.call(rbind, lapply(by_night, function(c) {
    worst <- c$speedup[which.max(abs(log(c$speedup)))]
    data.frame(run = c$run[1], date = c$date[1], version = c$version[1], svn_rev = c$svn_rev[1],
               n = nrow(c), faster = sum(c$speedup > 1), slower = sum(c$speedup < 1),
               worst = worst, final = all(c$final),
               benchmarks = paste(utils::head(c$benchmark[order(-abs(log(c$speedup)))], 4), collapse = ", "),
               stringsAsFactors = FALSE)
  }))
  out$kind <- ifelse(!out$final, "pending", ifelse(out$faster >= out$slower, "faster", "slower"))
  out[order(out$date, decreasing = TRUE), ]
}

#' Night-by-night change detection for R-devel, in the spirit of PHP's
#' benchmark visualisation: a benchmark is flagged on the night its log time
#' departs from the median of the previous `window` good nights by more than the
#' threshold and the interval, and the following nights confirm the new level.
#' The last `confirm` nights are "not final yet". Suspect sessions (sentinel
#' drift) are neither flagged nor used as reference.
devel_changes <- function(est, devel_runs, window = 7, confirm = 3) {
  devel_runs <- devel_runs[order(devel_runs$date), ]
  good <- devel_runs$run[!devel_runs$suspect]
  by_b <- split(est[est$run %in% devel_runs$run, ], est$benchmark[est$run %in% devel_runs$run])
  flags <- lapply(by_b, function(e) {
    e <- e[match(devel_runs$run, e$run), ]
    e$run <- devel_runs$run
    lm <- e$log_mean
    is_good <- devel_runs$run %in% good
    res <- list()
    prev_sign <- 0
    for (j in seq_along(lm)) {
      if (!is_good[j] || is.na(lm[j])) next
      past <- which(is_good[seq_len(j - 1)])
      past <- utils::tail(past, window)
      if (length(past) < 3) next
      ref <- stats::median(lm[past])
      d <- ref - lm[j]                       # > 0 => faster
      se <- e$log_se[j] * sqrt(1 + 1 / length(past))
      sig <- abs(exp(d) - 1) > CHANGE_THRESHOLD && abs(d) > tq(2 * (e$n[j] - 1)) * se
      if (!sig) { prev_sign <- 0; next }
      if (sign(d) == prev_sign) next          # same step, already reported
      fut <- which(is_good & seq_along(lm) > j)
      fut <- utils::head(fut, confirm)
      final <- length(fut) == confirm
      if (final && sign(ref - stats::median(lm[fut])) != sign(d)) next   # blip
      prev_sign <- sign(d)
      res[[length(res) + 1]] <- data.frame(
        run = devel_runs$run[j], benchmark = e$benchmark[1],
        speedup = exp(d), final = final, stringsAsFactors = FALSE)
    }
    do.call(rbind, res)
  })
  out <- do.call(rbind, flags)
  if (is.null(out)) return(data.frame())
  merge(out, devel_runs[, c("run", "date", "version", "svn_rev")], by = "run")
}
