# Synthetic results for the mockup. Every table has the shape the real ingest
# step will write into speedR-results/index, so swapping the mock for real
# data is a change of directory, not of code. Nothing here is a measurement.
#
#   Rscript R/mock.R [outdir]     (default: data/mock)

mock_releases <- function() {
  read.csv(text = "version,date
3.0.0,2013-04-03
3.0.1,2013-05-16
3.0.2,2013-09-25
3.0.3,2014-03-06
3.1.0,2014-04-10
3.1.1,2014-07-10
3.1.2,2014-10-31
3.1.3,2015-03-09
3.2.0,2015-04-16
3.2.1,2015-06-18
3.2.2,2015-08-14
3.2.3,2015-12-10
3.2.4,2016-03-10
3.2.5,2016-04-14
3.3.0,2016-05-03
3.3.1,2016-06-21
3.3.2,2016-10-31
3.3.3,2017-03-06
3.4.0,2017-04-21
3.4.1,2017-06-30
3.4.2,2017-09-28
3.4.3,2017-11-30
3.4.4,2018-03-15
3.5.0,2018-04-23
3.5.1,2018-07-02
3.5.2,2018-12-20
3.5.3,2019-03-11
3.6.0,2019-04-26
3.6.1,2019-07-05
3.6.2,2019-12-12
3.6.3,2020-02-29
4.0.0,2020-04-24
4.0.1,2020-06-06
4.0.2,2020-06-22
4.0.3,2020-10-10
4.0.4,2021-02-15
4.0.5,2021-03-31
4.1.0,2021-05-18
4.1.1,2021-08-10
4.1.2,2021-11-01
4.1.3,2022-03-10
4.2.0,2022-04-22
4.2.1,2022-06-23
4.2.2,2022-10-31
4.2.3,2023-03-15
4.3.0,2023-04-21
4.3.1,2023-06-16
4.3.2,2023-10-31
4.3.3,2024-02-29
4.4.0,2024-04-24
4.4.1,2024-06-14
4.4.2,2024-10-31
4.4.3,2025-02-28
4.5.0,2025-04-11
4.5.1,2025-06-13
4.5.2,2025-10-31
4.5.3,2026-03-11
4.6.0,2026-04-24
4.6.1,2026-06-24", stringsAsFactors = FALSE)
}

minor_of <- function(v) sub("^(\\d+\\.\\d+).*", "\\1", v)

version_key <- function(v) {
  p <- strsplit(v, ".", fixed = TRUE)
  vapply(p, function(x) sum(as.integer(x) * c(10000, 100, 1)), numeric(1))
}

# Per-minor multipliers on the time of each category group, relative to R 4.0.
# Shapes only loosely follow history (the 3.4 JIT, the 4.4 bcEval rework).
MINOR_FACTORS <- list(
  #           eval  prim  mem
  "3.0" = c(2.70, 1.10, 1.12),
  "3.1" = c(2.62, 1.09, 1.10),
  "3.2" = c(2.55, 1.08, 1.09),
  "3.3" = c(2.48, 1.07, 1.07),
  "3.4" = c(1.16, 1.05, 1.05),
  "3.5" = c(1.09, 1.03, 1.04),
  "3.6" = c(1.04, 1.02, 1.02),
  "4.0" = c(1.00, 1.00, 1.00),
  "4.1" = c(0.98, 0.99, 0.97),
  "4.2" = c(0.97, 0.98, 0.96),
  "4.3" = c(0.95, 0.98, 0.96),
  "4.4" = c(0.86, 0.97, 0.95),
  "4.5" = c(0.84, 0.96, 0.94),
  "4.6" = c(0.82, 0.95, 0.93)
)

group_factors <- function(v) {
  f <- MINOR_FACTORS[[minor_of(v)]]
  patch <- as.integer(sub(".*\\.", "", v))
  f <- f * (1 - 0.004 * patch)               # patch releases: tiny drift
  if (v == "4.3.0") f[3] <- f[3] * 1.07      # mock memory regression ...
  c(eval = f[1], prim = f[2], mem = f[3])    # ... fixed in 4.3.1
}

GROUP_OF <- c(
  interpreter = "eval", call = "eval", dispatch = "eval", lookup = "eval",
  primitives = "prim", `mem-alloc` = "mem", `mem-duplicate` = "mem",
  `mem-gc` = "mem", `native-ffi` = "native", `native-blas` = "native",
  unattributed = "native"
)

# Dirichlet-ish category shares at R 4.0.0, by suite archetype.
suite_alpha <- function(suite, name) {
  a <- switch(suite,
    shootout       = c(9, 6, 0.6, 4, 7, 2.5, 1.5, 2.5, 0.4, 0.1),
    areWeFast      = c(11, 7, 0.5, 5, 4, 2.5, 1, 2.5, 0.2, 0.1),
    RealThing      = c(4, 3, 2.5, 2, 8, 2, 2, 1.5, 1.5, 1.5),
    SpeedTest      = c(4, 2.5, 0.6, 2, 10, 2, 2, 2, 1, 2.5),
    riposte        = c(3, 2, 0.4, 1.5, 12, 3, 2.5, 3, 0.6, 1.2),
    mathkernel     = c(1.5, 0.6, 0.2, 0.5, 14, 2, 0.6, 1.2, 0.3, 0.4),
    `R-benchmark-25` = c(1, 0.6, 0.3, 0.4, 5, 1, 0.8, 0.8, 1, 14),
    misc           = c(10, 6, 0.4, 5, 5, 3, 1, 2, 0.2, 0.1)
  )
  if (grepl("^MMM", name)) a[10] <- 16
  if (grepl("flexclust$", name)) a[3] <- 8          # S4 dispatch
  if (grepl("^att3", name)) a[c(1, 5)] <- c(4, 9)    # "Programmation"
  a
}

rdirichlet1 <- function(alpha) { g <- rgamma(length(alpha), alpha); g / sum(g) }

mock_benchmarks <- function(registry) {
  set.seed(42)
  n <- nrow(registry)
  shares <- t(vapply(seq_len(n), function(i) {
    s <- rdirichlet1(suite_alpha(registry$suite[i], registry$name[i]))
    u <- runif(1, 0.005, 0.035)
    c(s * (1 - u), u)
  }, numeric(11)))
  colnames(shares) <- names(GROUP_OF)
  b <- registry
  b$id <- paste(b$suite, b$name, sep = "/")
  b$base_ms <- round(exp(runif(n, log(250), log(2400))))
  b$min_version <- "3.0.0"
  # benchmarks that need R >= 4.1 (native pipe / \(x) lambdas) or newer packages
  b$min_version[sample(n, 9)] <- "4.1.0"
  b$min_version[b$suite == "riposte" & grepl("kmeans|lr|pca", b$name)] <- "3.3.0"
  list(meta = b, shares = shares)
}

# Time of benchmark i at version v (ms), and its category shares there.
model_time <- function(base_ms, share0, v, extra = c(eval = 1, prim = 1, mem = 1, native = 1)) {
  f <- c(group_factors(v), native = 1) * extra
  parts <- base_ms * share0 * f[GROUP_OF[names(share0)]]
  list(time = sum(parts), shares = parts / sum(parts))
}

MACHINES <- data.frame(
  machine   = c("prl-bench-x64-1", "prl-bench-arm64-1", "prl-mac-m4-1"),
  os        = c("linux", "linux", "macos"),
  arch      = c("x86_64", "aarch64", "arm64"),
  cpu       = c("AMD Ryzen 9 7950X (mock)", "Ampere Altra Q80-30 (mock)", "Apple M4 (mock)"),
  kernel    = c("Linux 6.17 (Ubuntu 26.04 LTS)", "Linux 6.17 (Ubuntu 26.04 LTS)", "macOS 26.1"),
  toolchain = c("gcc 13.3, gfortran 13.3, OpenBLAS 0.3.26 (image sha256:3f1c…)",
                "gcc 13.3, gfortran 13.3, OpenBLAS 0.3.26 (image sha256:9ab0…)",
                "Apple clang 17, gfortran 14.2 (mac.r-project.org), vecLib"),
  profiler  = c("perf (dwarf,32768)", "perf (dwarf,32768)", "samply"),
  profiles  = c("validated", "experimental", "experimental"),
  wake      = c("wol", "ipmi", "always-on"),
  speed     = c(1.00, 1.38, 0.82),
  noise     = c(0.010, 0.014, 0.030),
  first_version = c("3.0.0", "4.0.0", "4.2.0"),
  stringsAsFactors = FALSE
)

CONFIG_EXTRA <- list(
  `default`     = c(eval = 1.00, prim = 1.00, mem = 1.00, native = 1.00),
  `no-bytecode` = c(eval = 2.35, prim = 1.00, mem = 1.04, native = 1.00),
  `lto`         = c(eval = 0.95, prim = 0.97, mem = 0.98, native = 1.00),
  `gc-a`        = c(eval = 1.00, prim = 1.00, mem = 0.90, native = 1.00),
  `gc-b`        = c(eval = 1.00, prim = 1.00, mem = 1.06, native = 1.00),
  `pgo`         = c(eval = 0.91, prim = 0.95, mem = 0.97, native = 1.00),
  `refblas`     = c(eval = 1.00, prim = 1.00, mem = 1.00, native = 2.60)
)

generate_mock <- function(outdir = "data/mock", registry_path = "data/benchmarks.csv") {
  dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
  registry <- read.csv(registry_path, stringsAsFactors = FALSE)
  bm <- mock_benchmarks(registry)
  b <- bm$meta
  rel <- mock_releases()
  set.seed(7)

  # machine x benchmark interaction (same CPU, different micro-architecture)
  inter <- matrix(exp(rnorm(nrow(b) * nrow(MACHINES), 0, 0.08)), nrow(b))

  runs <- list(); res <- list(); prof <- list()
  run_id <- 0L
  add_run <- function(machine, version, config, kind, date, svn_rev, extra, mi,
                      suspect = FALSE, shift = NULL) {
    run_id <<- run_id + 1L
    m <- MACHINES[mi, ]
    ok <- version_key(b$min_version) <= version_key(if (kind == "devel") "4.6.1" else version)
    rows <- vector("list", nrow(b)); prow <- vector("list", nrow(b))
    for (i in seq_len(nrow(b))) {
      mt <- model_time(b$base_ms[i], bm$shares[i, ], if (kind == "devel") "4.6.1" else version, extra)
      t <- mt$time * m$speed * inter[i, mi]
      if (!is.null(shift)) t <- t * shift[i]
      if (suspect) t <- t * 1.05
      proc <- if (ok[i]) t * exp(rnorm(5, 0, m$noise)) else rep(NA_real_, 5)
      rss <- if (ok[i]) unname(round(60 + 900 * bm$shares[i, "mem-alloc"] + rnorm(1, 0, 4))) else NA
      gc <- if (ok[i]) proc * unname(mt$shares["mem-gc"]) else rep(NA_real_, 5)
      rows[[i]] <- data.frame(run = run_id, benchmark = b$id[i], process = 1:5,
                              time_ms = round(proc, 2), gc_ms = round(gc, 2),
                              max_rss_mb = rss)
      if (ok[i] && config == "default") {
        sh <- mt$shares * exp(rnorm(11, 0, 0.04))   # multiplicative: small shares stay > 0
        sh <- sh / sum(sh)
        prow[[i]] <- data.frame(run = run_id, benchmark = b$id[i],
                                category = names(sh), share = round(unname(sh), 5))
      }
    }
    runs[[run_id]] <<- data.frame(
      run = run_id, machine = machine, impl = "gnur", version = version,
      kind = kind, config = config, date = date, svn_rev = svn_rev,
      suspect = suspect, sentinel_drift = round(if (suspect) 0.052 else rnorm(1, 0, 0.006), 4),
      n_ok = sum(ok), n_total = nrow(b), stringsAsFactors = FALSE)
    res[[run_id]] <<- do.call(rbind, rows)
    prof[[run_id]] <<- do.call(rbind, prow)
  }

  # releases, on every machine from its first version on
  for (mi in seq_len(nrow(MACHINES))) {
    m <- MACHINES[mi, ]
    for (k in seq_len(nrow(rel))) {
      v <- rel$version[k]
      if (version_key(v) < version_key(m$first_version)) next
      add_run(m$machine, v, "default", "release", rel$date[k], NA_integer_,
              CONFIG_EXTRA$default, mi)
    }
  }

  # configurations on the reference machine, last patch of each 4.x minor
  last_patch <- tapply(rel$version, minor_of(rel$version), function(x) x[which.max(version_key(x))])
  cfg_versions <- unname(last_patch[grepl("^4", names(last_patch))])
  for (v in cfg_versions) for (cfg in setdiff(names(CONFIG_EXTRA), "default")) {
    if (cfg == "pgo" && v != "4.6.1") next
    add_run("prl-bench-x64-1", v, cfg, "release", rel$date[rel$version == v],
            NA_integer_, CONFIG_EXTRA[[cfg]], 1L)
  }

  # nightly R-devel on the reference machine
  nights <- seq(as.Date("2026-05-04"), as.Date("2026-11-09"), by = "day")
  disp_heavy <- bm$shares[, "dispatch"] > 0.06
  look_heavy <- bm$shares[, "lookup"] > 0.08
  rev <- 89400L
  for (j in seq_along(nights)) {
    rev <- rev + sample(2:14, 1)
    shift <- rep(1, nrow(b))
    if (j >= 41 && j < 53) shift[disp_heavy] <- 1.09     # regression ...
    if (j >= 121) shift[look_heavy] <- shift[look_heavy] * 0.955  # speedup
    shift <- shift * (1 - 0.00008 * j)
    add_run("prl-bench-x64-1", paste0("devel@r", rev), "default", "devel",
            as.character(nights[j]), rev, CONFIG_EXTRA$default, 1L,
            suspect = (j == 88), shift = shift)
  }

  runs <- do.call(rbind, runs)
  res <- do.call(rbind, res)
  prof <- do.call(rbind, prof)

  events <- data.frame(
    machine = c("prl-bench-x64-1", "prl-bench-x64-1", "prl-bench-arm64-1", "prl-mac-m4-1"),
    date = c("2026-07-14", "2026-10-02", "2026-09-01", "2026-09-20"),
    event = c("Kernel 6.17.0-21 → 6.17.0-27 (maintenance window)",
              "BIOS 1.2.3 → 1.2.5, SMT re-disabled",
              "Machine added (IPMI wake)",
              "macOS 26.0 → 26.1"),
    stringsAsFactors = FALSE)

  wz <- function(x, f) { con <- gzfile(file.path(outdir, f), "w"); on.exit(close(con)); write.csv(x, con, row.names = FALSE) }
  write.csv(b[, c("id", "suite", "name", "min_version")], file.path(outdir, "benchmarks.csv"), row.names = FALSE)
  write.csv(MACHINES[, setdiff(names(MACHINES), c("speed", "noise"))], file.path(outdir, "machines.csv"), row.names = FALSE)
  write.csv(runs, file.path(outdir, "runs.csv"), row.names = FALSE)
  write.csv(events, file.path(outdir, "events.csv"), row.names = FALSE)
  wz(res, "samples.csv.gz")
  wz(prof, "profiles.csv.gz")
  writeLines(c("This directory is SYNTHETIC mock data for the dashboard mockup.",
               "It is generated by R/mock.R and contains no measurements."),
             file.path(outdir, "README"))
  invisible(list(runs = runs, samples = res, profiles = prof))
}

if (sys.nframe() == 0L) {
  args <- commandArgs(trailingOnly = TRUE)
  generate_mock(if (length(args)) args[[1]] else "data/mock")
}
