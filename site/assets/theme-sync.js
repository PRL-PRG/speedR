// Re-colour plotly charts when the reader toggles light/dark.
//
// Charts are authored with LIGHT tokens (R/palette.R). window.RS_THEME_MAP
// (written by the pre-render step from the same file) maps every light value
// to its dark twin; on a toggle each chart's original spec is re-rendered
// with the values swapped. Hidden tabs are resized when they are shown.
(function () {
  const isDark = () => document.body.classList.contains("quarto-dark");

  function swap(json, map) {
    const keys = Object.keys(map).sort((a, b) => b.length - a.length);
    if (!keys.length) return json;
    const esc = keys.map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
    const re = new RegExp(esc.join("|"), "gi");
    const lower = {};
    for (const k of keys) lower[k.toLowerCase()] = map[k];
    return json.replace(re, (m) => lower[m.toLowerCase()] ?? m);
  }

  function apply() {
    const map = window.RS_THEME_MAP || {};
    const dark = isDark();
    document.querySelectorAll(".js-plotly-plot").forEach((gd) => {
      if (!gd.data || !window.Plotly) return;
      if (!gd.__rsLight) {
        gd.__rsLight = JSON.stringify({ data: gd.data, layout: gd.layout });
      }
      if (gd.__rsDark === dark) return;
      const spec = JSON.parse(dark ? swap(gd.__rsLight, map) : gd.__rsLight);
      gd.__rsDark = dark;
      window.Plotly.react(gd, spec.data, spec.layout, gd._context);
    });
  }

  function schedule() { window.setTimeout(apply, 0); }

  // recolour each widget as soon as htmlwidgets has rendered it
  if (window.HTMLWidgets && window.HTMLWidgets.addPostRenderHandler) {
    window.HTMLWidgets.addPostRenderHandler(schedule);
  }

  window.addEventListener("load", () => {
    schedule();
    new MutationObserver(schedule).observe(document.body, { attributes: true, attributeFilter: ["class"] });
    // widgets render asynchronously; catch late ones once more
    window.setTimeout(apply, 600);
  });

  document.addEventListener("shown.bs.tab", () => {
    window.dispatchEvent(new Event("resize"));
    schedule();
  });
})();
