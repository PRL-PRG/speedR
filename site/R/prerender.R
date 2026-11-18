# Quarto pre-render step (runs from the project root):
#   1. make sure there is data (generate the mock if rendering without results),
#   2. refresh the Ubuntu LTS table that picks the baseline release,
#   3. build the cache every page reads,
#   4. write the generated head/banner includes,
#   5. write one stub page per benchmark.

source("R/palette.R")
source("R/load.R")
source("R/stats.R")
source("R/ubuntu.R")

if (is_mock() && !file.exists(file.path("data", "mock", "samples.csv"))) {
  message("pre-render: generating mock data")
  source("R/mock.R")
  generate_mock("data/mock")
}

# the baseline follows the newest Ubuntu LTS; refresh before the cache is built
lts <- update_ubuntu_lts(file.path("data", "ubuntu-lts.csv"))
message("pre-render: baseline R ", lts$r[nrow(lts)], " (Ubuntu ", lts$ubuntu[nrow(lts)], " LTS)")

dir.create(file.path("data", "_cache"), showWarnings = FALSE, recursive = TRUE)
message("pre-render: building cache from ", results_dir())
build_cache()
d <- readRDS(cache_path())

writeLines(c(
  "<script>",
  paste0("window.RS_THEME_MAP = ", jsonlite::toJSON(theme_map(), auto_unbox = TRUE), ";"),
  "</script>"
), file.path("assets", "_generated-head.html"))

writeLines(c("<script>", readLines(file.path("assets", "theme-sync.js")), "</script>"),
           file.path("assets", "_generated-after.html"))

banner <- if (d$mock) {
  paste0(
    '<div class="rs-mock-banner" role="note"><strong>Mockup:</strong> ',
    "synthetic data, not measurements of R.</div>"
  )
} else ""
writeLines(banner, file.path("assets", "_banner.html"))

# one page per benchmark: benchmarks/<suite>--<name with / as -->.qmd
old <- list.files("benchmarks", pattern = "--.*\\.qmd$", full.names = TRUE)
unlink(old)
for (i in seq_len(nrow(d$benchmarks))) {
  b <- d$benchmarks[i, ]
  slug <- gsub("/", "--", b$id, fixed = TRUE)
  short <- basename(b$name)
  writeLines(c(
    "---",
    sprintf('title: "%s"', short),
    sprintf('subtitle: "%s · %s"', b$suite, b$name),
    "search: true",
    "---",
    "",
    "```{r}",
    "#| include: false",
    'source("R/site.R")',
    sprintf('BENCH <- "%s"', b$id),
    "```",
    "",
    "{{< include ../_benchmark-body.qmd >}}"
  ), file.path("benchmarks", paste0(slug, ".qmd")))
}
message("pre-render: wrote ", nrow(d$benchmarks), " benchmark pages")
