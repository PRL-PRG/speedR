# Which R each Ubuntu LTS ships. The newest LTS sets the site-wide baseline
# (stats.R), so when a new LTS is released the next render rescales every
# speedup to its R.
#
# The list of releases comes from Debian's distro-info-data (fast, marks LTS
# explicitly). The R an LTS shipped never changes after release, so Launchpad
# (slow and intermittent) is asked only about an LTS that data/ubuntu-lts.csv
# does not have yet, i.e. once every two years.

DISTRO_INFO <- "https://debian.pages.debian.net/distro-info-data/ubuntu.csv"
LP_API <- "https://api.launchpad.net/devel/ubuntu"

#' GET a URL's body as text, with a few tries.
http_get <- function(url, tries = 3, timeout = 45) {
  h <- curl::new_handle(timeout = timeout, useragent = "speedR (https://github.com/PRL-PRG/speedR)")
  for (i in seq_len(tries)) {
    res <- tryCatch(curl::curl_fetch_memory(url, handle = h), error = function(e) e)
    if (!inherits(res, "error") && res$status_code == 200) return(rawToChar(res$content))
  }
  stop(if (inherits(res, "error")) conditionMessage(res) else paste("HTTP", res$status_code, "for", url),
       call. = FALSE)
}

#' Released Ubuntu LTS series: version, codename, release date.
fetch_lts_series <- function(today = Sys.Date()) {
  # rows have more fields than the header (ESM dates), so split them by hand
  lines <- strsplit(http_get(DISTRO_INFO, timeout = 15), "\n", fixed = TRUE)[[1]][-1]
  f <- strsplit(lines[nzchar(lines)], ",", fixed = TRUE)
  d <- data.frame(version = vapply(f, `[`, "", 1), codename = vapply(f, `[`, "", 3),
                  released = vapply(f, `[`, "", 5), stringsAsFactors = FALSE)
  d <- d[grepl(" LTS$", d$version) & as.Date(d$released) <= today, ]
  d$version <- sub(" LTS$", "", d$version)
  d
}

#' The r-base version published in a series' release pocket, e.g. "4.5.2".
fetch_r_in_series <- function(codename) {
  url <- paste0(LP_API, "/+archive/primary?ws.op=getPublishedSources",
                "&source_name=r-base&exact_match=true&pocket=Release",
                "&distro_series=", LP_API, "/", codename)
  src <- jsonlite::fromJSON(http_get(url))$entries
  if (!length(src) || !nrow(src)) stop("no r-base in ", codename, call. = FALSE)
  pub <- src[src$status == "Published", ]
  deb <- if (nrow(pub)) pub$source_package_version[1] else src$source_package_version[1]
  sub("-[^-]*$", "", sub("^\\d+:", "", deb))       # drop epoch and Debian revision
}

#' Add any LTS newer than the newest one in `path`. A failure (offline, or
#' Launchpad down) leaves the table, and so the baseline, as it was.
update_ubuntu_lts <- function(path) {
  known <- if (file.exists(path)) {
    utils::read.csv(path, stringsAsFactors = FALSE, colClasses = "character")
  } else UBUNTU_LTS_FALLBACK
  tryCatch({
    series <- fetch_lts_series()
    new <- series[numeric_version(series$version) > max(numeric_version(known$ubuntu)), ]
    for (i in seq_len(nrow(new))) {
      r <- fetch_r_in_series(new$codename[i])
      message("pre-render: new Ubuntu LTS ", new$version[i], " ships R ", r)
      known <- rbind(known, data.frame(ubuntu = new$version[i], r = r, stringsAsFactors = FALSE))
    }
  }, error = function(e) {
    warning("could not check for a new Ubuntu LTS (", conditionMessage(e), "); keeping the saved table",
            call. = FALSE)
  })
  known <- known[order(numeric_version(known$ubuntu)), ]
  utils::write.csv(known, path, row.names = FALSE)
  known
}
