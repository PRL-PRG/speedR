# Small HTML building blocks shared by the pages. Styling lives in
# assets/*.scss; nothing here sets a colour inline.

fmt_speedup <- function(x, digits = 2) {
  ifelse(is.na(x), "–", paste0(formatC(x, format = "f", digits = digits), "×"))
}

fmt_change <- function(speedup, digits = 1) {
  # speedup > 1 means faster; report the time change the reader feels
  pct <- (1 / speedup - 1) * 100
  ifelse(is.na(pct), "–",
         paste0(ifelse(pct > 0, "+", "−"), formatC(abs(pct), format = "f", digits = digits), "% time"))
}

fmt_ms <- function(x) {
  ifelse(is.na(x), "–",
         ifelse(x >= 1000, paste0(formatC(x / 1000, format = "f", digits = 2), " s"),
                paste0(formatC(x, format = "f", digits = 0), " ms")))
}

fmt_date <- function(d) format(as.Date(d), "%e %b %Y")

tiles <- function(...) div(class = "rs-tiles", ...)

tile <- function(label, value, sub = NULL, badge = NULL) {
  div(class = "rs-tile",
      div(class = "rs-tile-label", label, badge),
      div(class = "rs-tile-value", value),
      if (!is.null(sub)) div(class = "rs-tile-sub", sub))
}

badge <- function(text, kind = "neutral", title = NULL) {
  span(class = paste0("rs-badge rs-badge-", kind), title = title, text)
}

# Status always carries an icon and a word, never colour alone.
status <- function(kind) {
  switch(kind,
    faster    = span(class = "rs-status rs-status-good", "▲ faster"),
    slower    = span(class = "rs-status rs-status-critical", "▼ slower"),
    same      = span(class = "rs-status rs-status-neutral", "● no change"),
    suspect   = span(class = "rs-status rs-status-warning", "⚠ suspect session"),
    pending   = span(class = "rs-status rs-status-neutral", "◌ not final yet"),
    validated = span(class = "rs-status rs-status-good", "✓ validated"),
    experimental = span(class = "rs-status rs-status-warning", "⚠ experimental")
  )
}

machine_label <- function(m) {
  r <- D$machines[D$machines$machine == m, ]
  paste0(r$os, " ", r$arch, " · ", m)
}

machine_badge <- function(m) {
  r <- D$machines[D$machines$machine == m, ]
  if (r$profiles == "validated") NULL
  else badge("experimental profiles", "experimental",
             title = paste("Profiles from", r$profiler, "are not yet validated against perf"))
}

#' Bootstrap 5 tabs built by hand, so a tab can hold htmlwidgets and still be
#' printed as one object (knitr keeps the widget dependencies).
tabs <- function(panels, id = paste0("tabs-", as.hexmode(sample.int(.Machine$integer.max, 1)))) {
  labels <- names(panels)
  ids <- paste0(id, "-", seq_along(panels))
  nav <- tags$ul(class = "nav nav-tabs rs-tabs", role = "tablist",
    lapply(seq_along(panels), function(i) {
      tags$li(class = "nav-item", role = "presentation",
        tags$button(class = paste("nav-link", if (i == 1) "active"),
                    `data-bs-toggle` = "tab", `data-bs-target` = paste0("#", ids[i]),
                    type = "button", role = "tab", labels[[i]]))
    }))
  content <- div(class = "tab-content",
    lapply(seq_along(panels), function(i) {
      div(class = paste("tab-pane fade", if (i == 1) "show active"), id = ids[i],
          role = "tabpanel", panels[[i]])
    }))
  div(class = "rs-tabset", nav, content)
}

machine_tabs <- function(machines, fun) {
  panels <- lapply(machines, function(m) tagList(machine_badge(m), fun(m)))
  names(panels) <- vapply(machines, machine_label, "")
  tabs(panels)
}

rs_table <- function(data, searchable = FALSE, defaultPageSize = 15, ...) {
  reactable(
    data, compact = TRUE, highlight = TRUE, searchable = searchable,
    defaultPageSize = defaultPageSize, showPageSizeOptions = FALSE,
    theme = reactableTheme(
      color = "var(--rs-ink)", backgroundColor = "transparent",
      borderColor = "var(--rs-grid)", stripedColor = "var(--rs-stripe)",
      highlightColor = "var(--rs-hover)",
      headerStyle = list(color = "var(--rs-ink2)", fontWeight = 600,
                         borderBottom = "1px solid var(--rs-axis)"),
      inputStyle = list(backgroundColor = "var(--rs-surface)", color = "var(--rs-ink)"),
      pageButtonStyle = list(color = "var(--rs-ink2)"),
      cellStyle = list(fontVariantNumeric = "tabular-nums")
    ),
    ...
  )
}

bench_url <- function(id, from = ".") {
  slug <- gsub("/", "--", id, fixed = TRUE)
  file.path(from, "benchmarks", paste0(slug, ".html"))
}
