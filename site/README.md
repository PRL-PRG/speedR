# speedR: dashboard (Quarto + R)

Static site showing GNU R performance across releases, R-devel nights,
configurations and platforms, with per-benchmark profiles.

**Status: mockup.** Without results it renders synthetic data from
`R/mock.R`, and every page carries a banner saying so.

## Render

    quarto render            # whole site into _site/
    quarto preview           # live preview while editing

Requires Quarto ≥ 1.11 and R with `htmltools`, `plotly`, `reactable`,
`jsonlite`, `knitr`, `rmarkdown`.

To render real data, point `SPEEDR_RESULTS` at a checkout of the
speedR-results index (same tables as `data/mock/`):

    SPEEDR_RESULTS=../../speedR-results/index quarto render

## Layout

| path | what |
|---|---|
| `R/prerender.R` | runs before every render: mock data if needed, the cache, one page per benchmark |
| `R/load.R` | where data comes from; builds `data/_cache/site.rds` |
| `R/stats.R` | estimates, speedups, geomeans, R-devel change detection |
| `R/palette.R` | colour tokens (validated light/dark palette) and category groups |
| `R/plots.R`, `R/ui.R` | plotly conventions, tiles, tabs, tables |
| `R/mock.R` | synthetic results with the real schema |
| `*.qmd` | pages; `_benchmark-body.qmd` is the per-benchmark template |
| `assets/` | themes, CSS, and the script that recolours charts in dark mode |
