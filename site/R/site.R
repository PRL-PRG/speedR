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
