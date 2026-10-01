/* Client-only slider search on the result page. Synonyms map to control names, not labels. */
(function (global) {
  const SYNONYMS = {
    gehalt: "gross",
    einkommen: "gross",
    lohn: "gross",
    hausgeld: "owner_costs",
    miete: "kaltmiete",
    zins: "sollzins",
    depot: "etf_return",
  };

  const TARGET_MATCHERS = {
    gross: (name) => name.startsWith("gross-"),
    owner_costs: (name) => name === "owner_costs",
    kaltmiete: (name) => name.startsWith("rent-") || name === "shared_kaltmiete",
    sollzins: (name) => name === "sollzins",
    etf_return: (name) => name === "etf_return",
  };

  function normalizeQuery(query) {
    return String(query || "")
      .trim()
      .toLowerCase()
      .normalize("NFD")
      .replace(/\p{M}/gu, "")
      .replace(/ß/g, "ss");
  }

  function synonymTarget(normalizedQuery) {
    if (!normalizedQuery || /^\d+([.,]\d+)?$/.test(normalizedQuery)) return null;
    return SYNONYMS[normalizedQuery] || null;
  }

  function labelText(control) {
    const caption = control.querySelector(".control-label");
    if (!caption) return "";
    return normalizeQuery(caption.childNodes[0]?.textContent || caption.textContent);
  }

  function controlsForTarget(controls, target) {
    const match = TARGET_MATCHERS[target];
    if (!match) return [];
    return controls.filter((control) => match(control.dataset.controlName || ""));
  }

  function findBeliefControls(beliefsRoot, rawQuery) {
    if (!beliefsRoot) return [];
    const normalized = normalizeQuery(rawQuery);
    if (!normalized) return [];
    const controls = [...beliefsRoot.querySelectorAll(".control[data-control-name]")];
    const target = synonymTarget(normalized);
    if (target) {
      const hits = controlsForTarget(controls, target);
      if (hits.length) return hits;
    }
    return controls.filter((control) => {
      const label = labelText(control);
      return label && label.includes(normalized);
    });
  }

  function findBeliefControl(beliefsRoot, rawQuery) {
    return findBeliefControls(beliefsRoot, rawQuery)[0] || null;
  }

  const api = {
    normalizeQuery,
    synonymTarget,
    findBeliefControl,
    findBeliefControls,
    SYNONYMS,
  };

  global.BeliefSearch = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof window !== "undefined" ? window : globalThis);
