# Sourced by the setup chunk of every page (execute-dir is the project root).

suppressPackageStartupMessages({
  library(htmltools)
  library(plotly)
  library(reactable)
})

for (f in c("palette.R", "stats.R", "load.R", "ui.R", "plots.R")) {
  source(file.path("R", f), local = FALSE)
}

knitr::opts_chunk$set(echo = FALSE, warning = FALSE, message = FALSE)

D <- site_data()
REF_MACHINE <- D$machines$machine[1]
METHODOLOGY <- D$methodology
METHODOLOGY_VERSIONS <- D$methodology_versions

# what the results have so far: pages and sections without data say so
HAS_PROFILES <- nrow(D$profiles) > 0
HAS_DEVEL <- any(D$runs$kind == "devel")
HAS_CONFIGS <- any(D$runs$config != "default")
not_yet <- function(text) div(class = "rs-empty", tags$strong(text))
