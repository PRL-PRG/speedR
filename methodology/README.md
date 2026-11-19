# Methodology versions

A methodology version fixes everything that decides what a number means: how
R is built, which benchmarks run and with what inputs, the run design, the
machine settings and the statistics. Every run records the version it was
measured under (`methodology` in `meta.json` and `runs.csv`), and the
dashboard shows each version on its own: numbers from two versions are never
compared or mixed.

| file | what |
|---|---|
| [`versions.csv`](versions.csv) | every version: number, status, date, one-line summary |
| `<version>.qmd` | the full text of a version, shown on the dashboard's Methodology page (markdown and inline R only: no code chunks) |

## Rules

- **0.x versions are drafts.** They may still change while the method is
  being settled, and their results can be thrown away.
- **From 1.0 a version is frozen** (`status = frozen`): its text and
  everything it describes never change again. A change to the method is a new
  version, and the old one stays on the dashboard with its results.
- The newest version in `versions.csv` is the one new runs use and the one
  the dashboard opens on.
- Anything that can move the numbers (compiler, flags, suite commit, run
  design, kernel or machine settings, statistics) needs a new version once the
  current one is frozen.
