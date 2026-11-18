# Plotly conventions for the site: transparent surfaces, hairline grid,
# system sans, one y-axis, legend on top. Colours are LIGHT tokens; the
# theme-sync script swaps them for DARK twins at runtime.

FONT <- "system-ui, -apple-system, 'Segoe UI', sans-serif"

ax <- function(title = NULL, ...) {
  utils::modifyList(list(
    title = list(text = title, font = list(color = LIGHT[["ink2"]], size = 13)),
    gridcolor = LIGHT[["grid"]], linecolor = LIGHT[["axis"]], showline = TRUE,
    zeroline = FALSE, ticks = "", tickfont = list(color = LIGHT[["muted"]], size = 12),
    automargin = TRUE
  ), list(...))
}

rs_layout <- function(p, x = ax(), y = ax(), legend = TRUE, hover = "closest", ...) {
  p |>
    layout(
      font = list(family = FONT, size = 13, color = LIGHT[["ink2"]]),
      paper_bgcolor = "rgba(0,0,0,0)", plot_bgcolor = "rgba(0,0,0,0)",
      xaxis = x, yaxis = y, hovermode = hover,
      hoverlabel = list(bgcolor = LIGHT[["surface"]], bordercolor = LIGHT[["axis"]],
                        font = list(color = LIGHT[["ink"]], family = FONT)),
      showlegend = legend,
      legend = list(orientation = "h", x = 0, xanchor = "left", y = 1.02, yanchor = "bottom",
                    traceorder = "normal",
                    font = list(color = LIGHT[["ink2"]]), bgcolor = "rgba(0,0,0,0)"),
      margin = list(l = 10, r = 10, t = if (legend) 40 else 10, b = 10),
      ...
    ) |>
    config(displaylogo = FALSE, responsive = TRUE,
           modeBarButtonsToRemove = c("lasso2d", "select2d", "autoScale2d",
                                      "toggleSpikelines", "hoverClosestCartesian",
                                      "hoverCompareCartesian"))
}

#' Speedup axis on a log scale with 1× always labelled (in bold): the
#' baseline is the anchor every other value is read against.
speedup_axis <- function(title, values, pad_below = 1.03) {
  steps <- c(0.1, 0.2, 0.25, 0.33, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1, 1.1, 1.25, 1.5, 2, 3, 4, 5)
  lo <- min(values, 1, na.rm = TRUE) / pad_below
  hi <- max(values, 1, na.rm = TRUE) * 1.03
  ticks <- steps[steps >= lo & steps <= hi]
  if (length(ticks) < 4) {          # narrow range: step in 2.5% instead
    fine <- round(seq(0.8, 1.2, by = 0.025), 3)
    ticks <- fine[fine >= lo & fine <= hi]
  }
  while (length(ticks) > 9) ticks <- ticks[ticks == 1 | seq_along(ticks) %% 2 == match(1, ticks) %% 2]
  text <- ifelse(ticks == 1, "<b>1×</b>", paste0(formatC(ticks, format = "f", digits = if (all(ticks * 100 == round(ticks * 100))) 2 else 3), "×"))
  ax(title, type = "log", tickvals = ticks, ticktext = text, range = log10(c(lo, hi)))
}

#' The horizontal reference line at 1×.
baseline_line <- function() {
  list(type = "line", xref = "paper", x0 = 0, x1 = 1, y0 = 1, y1 = 1, layer = "below",
       line = list(color = LIGHT[["muted"]], width = 1.5, dash = "dot"))
}

#' Release points: R versions shipped in an Ubuntu LTS are drawn as larger
#' dark diamonds, the rest as plain dots. `y` and `hover` are vectors
#' parallel to the rows of `d`; label the diamonds with lts_labels().
add_release_markers <- function(p, d, y, hover, size = 8) {
  lts <- is_lts(d$version)
  p |>
    add_markers(x = d$date[!lts], y = y[!lts], name = "Release", inherit = FALSE,
                marker = list(color = LIGHT[["series1"]], size = size,
                              line = list(color = LIGHT[["surface"]], width = 2)),
                text = hover[!lts], hoverinfo = "text") |>
    add_markers(x = d$date[lts], y = y[lts], name = "Shipped in an Ubuntu LTS", inherit = FALSE,
                marker = list(color = LIGHT[["ink"]], size = size + 6, symbol = "diamond",
                              line = list(color = LIGHT[["surface"]], width = 2)),
                text = hover[lts], hoverinfo = "text")
}

#' Labels hung below each LTS diamond (the line climbs to the right, so the
#' space underneath is free). Annotations on a log axis take log10 units.
lts_labels <- function(d, y, log = TRUE) {
  lts <- which(is_lts(d$version))
  lapply(lts, function(i) list(
    x = d$date[i], y = if (log) log10(y[i]) else y[i],
    text = paste0("<b>", d$version[i], "</b><br>", lts_name(d$version[i])),
    showarrow = TRUE, arrowhead = 0, arrowwidth = 1, arrowcolor = LIGHT[["axis"]],
    ax = 0, ay = 34, standoff = 8, yanchor = "top",
    font = list(color = LIGHT[["ink2"]], size = 11)))
}

#' Release timeline: geomean speedup vs the machine's baseline, CI band,
#' one series; annotated where the story is.
plot_release_timeline <- function(tl, baseline_version, height = 400, annotate = TRUE) {
  tl <- tl[order(tl$date), ]
  hover <- sprintf("<b>R %s</b>%s · %s<br>%s vs R %s<br>95%% CI %s – %s<br>%d benchmarks",
                   tl$version, ifelse(is_lts(tl$version), paste0(" (", lts_name(tl$version), " LTS)"), ""),
                   fmt_date(tl$date), fmt_speedup(tl$speedup), baseline_version,
                   fmt_speedup(tl$lo, 3), fmt_speedup(tl$hi, 3), tl$n)
  p <- plot_ly(tl, x = ~date, height = height) |>
    add_ribbons(ymin = ~lo, ymax = ~hi, fillcolor = LIGHT[["band"]],
                line = list(width = 0), hoverinfo = "skip", name = "95% CI", showlegend = FALSE) |>
    add_lines(y = ~speedup, line = list(color = LIGHT[["series1"]], width = 2, shape = "hv"),
              hoverinfo = "skip", showlegend = FALSE) |>
    add_release_markers(tl, tl$speedup, hover)
  ann <- lts_labels(tl, tl$speedup)
  if (annotate && "3.4.0" %in% tl$version) {
    r <- tl[tl$version == "3.4.0", ]
    # annotations on a log axis are placed in log10 units
    ann <- c(ann, list(list(x = r$date, y = log10(r$speedup), text = "3.4.0: JIT on by default",
                            showarrow = TRUE, arrowcolor = LIGHT[["muted"]], ax = -60, ay = -40,
                            font = list(color = LIGHT[["ink2"]], size = 12))))
  }
  last <- tl[nrow(tl), ]
  ann <- c(ann, list(list(x = last$date, y = log10(last$speedup), xanchor = "left",
                          text = paste0("<b>", fmt_speedup(last$speedup), "</b> R ", last$version),
                          showarrow = FALSE, xshift = 8, font = list(color = LIGHT[["ink"]], size = 12))))
  y_title <- paste0("Speedup vs R ", baseline_version,
                    if (is_lts(baseline_version)) paste0(" (", lts_name(baseline_version), ")"), ", ×")
  rs_layout(p, x = ax(NULL, type = "date"),
            y = speedup_axis(y_title, c(tl$lo, tl$hi), pad_below = 1.22),
            legend = TRUE, shapes = list(baseline_line()), annotations = ann) |>
    layout(margin = list(l = 10, r = 110, t = 40, b = 10))
}

#' Per-suite lines, coloured by the fixed suite order.
plot_suite_lines <- function(st, baseline_version, height = 380) {
  p <- plot_ly(height = height)
  for (s in intersect(SUITES, unique(st$suite))) {
    d <- st[st$suite == s, ]
    d <- d[order(d$date), ]
    p <- p |> add_lines(data = d, x = ~date, y = ~speedup, name = s,
                        line = list(color = SUITE_COLORS[[s]], width = 2, shape = "hv"),
                        text = sprintf("%s · R %s: %s (n=%d)", s, d$version, fmt_speedup(d$speedup), d$n),
                        hoverinfo = "text")
  }
  rs_layout(p, x = ax(NULL, type = "date"),
            y = speedup_axis(paste("Speedup vs R", baseline_version, "(×)"), st$speedup),
            shapes = list(baseline_line()))
}

#' Diverging colour scale for speedups on a log2 axis: blue faster, red slower.
diverging_scale <- function() {
  list(c(0, LIGHT[["div_slow2"]]), c(0.25, LIGHT[["div_slow1"]]), c(0.5, LIGHT[["div_mid"]]),
       c(0.75, LIGHT[["div_fast1"]]), c(1, LIGHT[["div_fast2"]]))
}

sequential_scale <- function() {
  list(c(0, LIGHT[["seq0"]]), c(0.35, LIGHT[["seq1"]]), c(0.7, LIGHT[["seq2"]]), c(1, LIGHT[["seq3"]]))
}

#' 100% stacked bars of category-group shares (4 validated hues + neutral).
plot_group_stack <- function(df, x, xlab = NULL, height = 360, horizontal = FALSE) {
  p <- plot_ly(height = height)
  for (g in GROUPS) {
    d <- df[df$group == g, ]
    if (!nrow(d)) next
    hover <- sprintf("<b>%s</b><br>%s: %.1f%%", d[[x]], g, 100 * d$share)
    p <- if (horizontal) {
      p |> add_bars(data = d, y = d[[x]], x = ~share, name = g, orientation = "h",
                    marker = list(color = GROUP_COLORS[[g]], line = list(color = LIGHT[["surface"]], width = 1)),
                    text = hover, hoverinfo = "text", textposition = "none")
    } else {
      p |> add_bars(data = d, x = d[[x]], y = ~share, name = g,
                    marker = list(color = GROUP_COLORS[[g]], line = list(color = LIGHT[["surface"]], width = 1)),
                    text = hover, hoverinfo = "text", textposition = "none")
    }
  }
  share_ax <- ax("Share of sampled time", tickformat = ".0%", range = c(0, 1))
  cat_ax <- ax(xlab, type = "category")
  cats <- if (is.factor(df[[x]])) levels(df[[x]]) else unique(df[[x]])
  if (any(is_lts(cats))) {          # release axes: the Ubuntu LTS versions stand out
    cat_ax$tickvals <- cats
    cat_ax$ticktext <- ifelse(is_lts(cats), paste0("<b>◆ ", cats, "</b>"), cats)
  }
  if (horizontal) rs_layout(p, x = share_ax, y = cat_ax, barmode = "stack", bargap = 0.25)
  else rs_layout(p, x = cat_ax, y = share_ax, barmode = "stack", bargap = 0.25)
}
