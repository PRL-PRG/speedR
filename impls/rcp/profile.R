# speedR, implementation rcp: sourced by the harness before the benchmark.
# After setup(), before the first iteration, every function the benchmark
# defined is replaced by its rcp-compiled version (rcp_cmpfun, as rcp's own
# benchmark harness compiles execute(); closures created inside a compiled
# function are compiled with it), so all compiling is outside the measured
# iterations. rcp's JIT (rcp_jit_enable) is not used. A function rcp cannot
# compile fails the benchmark rather than run as plain R.
suppressPackageStartupMessages(library(rcp))

rbench_prepare <- function() {
  # the harness's own functions share the global environment; the timing loop
  # stays as R runs it
  harness <- c("prepare", "iterate", "run", "rbench_prepare")
  if (!all(vapply(harness, exists, NA, envir = globalenv(), inherits = FALSE)))
    stop("the harness's functions are not ", paste(harness, collapse = ", "), ": update impls/rcp/profile.R")
  for (n in setdiff(ls(globalenv(), all.names = TRUE), harness)) {
    f <- get(n, globalenv())
    if (!is.function(f) || is.primitive(f)) next
    g <- rcp_cmpfun(f, options = list(optimize = 3L, cache = FALSE))
    if (!rcp_is_compiled(g)) stop("rcp could not compile ", n, "()")
    assign(n, g, envir = globalenv())
  }
}
