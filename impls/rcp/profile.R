# speedR, implementation rcp: sourced by the harness before the benchmark.
# After setup(), before the first iteration, execute() is replaced by its
# rcp-compiled version, as r-compile-server's own benchmark harness does it
# (client/rsh/inst/benchmarks/harness.R, --rcp); what execute() calls runs as
# R runs it. A benchmark rcp cannot compile fails rather than run as plain R.
suppressPackageStartupMessages(library(rcp))

rbench_prepare <- function() {
  execute <<- rcp_cmpfun(execute, options = list(optimize = 3L, cache = FALSE))
  if (!rcp_is_compiled(execute)) stop("rcp could not compile execute()")
}
