# Colour tokens for the whole site. Charts are written against these roles;
# `assets/theme-sync.js` swaps every light value for its dark twin when the
# reader toggles the theme, so each light hex here must be unique and must have
# an entry in `DARK`.
#
# Values come from the validated reference palette (dataviz skill,
# references/palette.md). Any change must be re-run through
# validate_palette.js in both modes.

LIGHT <- c(
  surface   = "#fcfcfb",
  ink       = "#0b0b0b",
  ink2      = "#52514e",
  muted     = "#898781",
  grid      = "#e1e0d9",
  axis      = "#c3c2b7",
  neutral   = "#b9b8b0",   # "unattributed" / reference marks
  series1   = "#2a78d6",
  series2   = "#eb6834",
  series3   = "#1baf7a",
  series4   = "#eda100",
  series5   = "#e87ba4",
  series6   = "#008300",
  series7   = "#6250d6",
  series8   = "#e34948",
  # diverging: faster (blue) <-> slower (red), grey midpoint
  div_fast2 = "#104281",
  div_fast1 = "#6da7ec",
  div_mid   = "#f0efec",
  div_slow1 = "#f3a39c",
  div_slow2 = "#b3261e",
  # sequential (blue) for shares
  seq0      = "#f4f8fd",
  seq1      = "#9ec5f4",
  seq2      = "#3987e5",
  seq3      = "#104281",
  band      = "rgba(42,120,214,0.16)"
)

DARK <- c(
  surface   = "#1a1a19",
  ink       = "#f0efec",
  ink2      = "#c3c2b7",
  muted     = "#8f8d86",
  grid      = "#2c2c2a",
  axis      = "#383835",
  neutral   = "#5f5e59",
  series1   = "#3987e5",
  series2   = "#d95926",
  series3   = "#199e70",
  series4   = "#c98500",
  series5   = "#d55181",
  series6   = "#008300",
  series7   = "#9085e9",
  series8   = "#e66767",
  div_fast2 = "#86b6ef",
  div_fast1 = "#2f5f9e",
  div_mid   = "#383835",
  div_slow1 = "#8a3a33",
  div_slow2 = "#f08c84",
  seq0      = "#1f2733",
  seq1      = "#1c4a85",
  seq2      = "#3987e5",
  seq3      = "#cde2fb",
  band      = "rgba(57,135,229,0.22)"
)

SERIES <- unname(LIGHT[paste0("series", 1:8)])

# The ten VMIL'26 categories, in the paper's order, and the four groups the
# stacked views use. Ten hues cannot pass the colour-vision checks, so the
# stacked charts colour by group (4 validated hues + a neutral) and the detail
# views (heatmap, tables) name every category.
CATEGORIES <- data.frame(
  category = c("interpreter", "call", "dispatch", "lookup", "primitives",
               "mem-alloc", "mem-duplicate", "mem-gc", "native-ffi", "native-blas",
               "unattributed"),
  group = c("Evaluation", "Evaluation", "Evaluation", "Evaluation", "Primitives",
            "Memory", "Memory", "Memory", "Native code", "Native code",
            "Unattributed"),
  description = c(
    "Bytecode and AST interpreter loops (bcEval, Rf_eval)",
    "Closure calls, argument matching, promises",
    "S3/S4 dispatch: UseMethod, NextMethod, standardGeneric",
    "Variable and function lookup in environments",
    "Built-in and primitive functions (do_*, ALTREP)",
    "Allocation of cons cells and vectors",
    "Copying values (duplicate, shallow_duplicate)",
    "Garbage collector",
    ".Call/.External/.C into package and system code",
    "BLAS/LAPACK linear algebra"
  )[c(1:10, NA)],
  stringsAsFactors = FALSE
)
CATEGORIES$description[11] <- "Samples no rule could attribute (shown, never hidden)"

GROUPS <- c("Evaluation", "Primitives", "Memory", "Native code", "Unattributed")
GROUP_COLORS <- c(
  "Evaluation"   = unname(LIGHT["series1"]),
  "Primitives"   = unname(LIGHT["series2"]),
  "Memory"       = unname(LIGHT["series3"]),
  "Native code"  = unname(LIGHT["series7"]),
  "Unattributed" = unname(LIGHT["neutral"])
)

SUITES <- c("shootout", "areWeFast", "RealThing", "SpeedTest", "riposte",
            "mathkernel", "R-benchmark-25", "misc")
SUITE_COLORS <- setNames(SERIES[seq_along(SUITES)], SUITES)

CONFIGS <- c("default", "no-bytecode", "lto", "gc-a", "gc-b", "pgo", "refblas")
CONFIG_COLORS <- setNames(SERIES[c(1, 2, 3, 4, 5, 6, 7)], CONFIGS)

# Mapping consumed by assets/theme-sync.js (light hex -> dark hex).
theme_map <- function() {
  keys <- intersect(names(LIGHT), names(DARK))
  stats::setNames(as.list(unname(DARK[keys])), unname(LIGHT[keys]))
}
