const euro = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

let scenario = null;
let latest = null;
let timer = null;
let requestId = 0;
let bundeslaender = ["Bayern"];
let scenarioSnapshot = null;
let touchedSnapshot = null;
function snapshotFromScenario() {
  scenarioSnapshot = structuredClone(scenario);
  touchedSnapshot = {
    sollzins: touched.sollzins,
    anschlusszins: touched.anschlusszins,
    pensions: { ...touched.pensions },
  };
}

function syncSaveRowButton() {
  const button = document.getElementById("save-row");
  if (button) button.hidden = !window.scenarioStore?.hasOpenRow?.();
}
let horizonMonthYear = null;
let horizonMonthYearBound = false;
let pathView = "both";

function pathViewFromScope(scope) {
  if (scope === "buy") return "buy";
  if (scope === "rent") return "rent";
  return "both";
}

function applyPathScopeFromScenario(body) {
  pathView = pathViewFromScope(body?.path_scope || "both");
}
const BUY_COLOR = "#0c8f62";
const RENT_COLOR = "#2a62b5";
const BUY_ETF_COLOR = "#0e9f6e";
const RENT_ETF_COLOR = "#3d7cc9";
const FLOW_LEFT_KEYS = new Set(["buy_left", "rent_left"]);
const FLOW_WARN_COLOR = "#9a3412";
const UBRIG_GREY = "#94a3b8";
const YEAR_TICK_MIN_GAP = 46;
const touched = { sollzins: false, anschlusszins: false, pensions: {} };

function percentDisplayDecimals(step) {
  const places = -Math.floor(Math.log10(step));
  return Math.max(0, places - 2);
}

function formatPercent(value, step) {
  const snapped = Math.round(Number(value) / step) * step;
  const digits = percentDisplayDecimals(step);
  return new Intl.NumberFormat("de-DE", {
    style: "percent",
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  }).format(snapped);
}

function setControlDisplay(label, value, unit, step) {
  const controls = document.querySelectorAll("#beliefs .control");
  for (const control of controls) {
    const caption = control.querySelector(".control-label");
    if (caption?.textContent !== label) continue;
    const range = control.querySelector('input[type="range"]');
    const out = control.querySelector("output");
    if (!range || !out) return;
    range.value = value;
    out.textContent = formatValue(Number(value), unit, step);
    paintRange(range);
    return;
  }
}

function syncHeaderAdvice() {
  const el = document.getElementById("header-advice");
  if (!el) return;
  const base = "Keine Finanz-, Steuer- oder Kreditempfehlung.";
  if (touched.sollzins || touched.anschlusszins) {
    el.textContent = `${base} Der Sollzins ist Ihre Angabe, kein Angebot.`;
  } else {
    el.textContent = `${base} Der Zinssatz ist ein Bundesbank-Durchschnitt, kein Angebot.`;
  }
}

function syncBeliefDisplays() {
  if (!latest) return;
  if (!touched.sollzins && latest.sollzins_used != null) {
    setControlDisplay("Sollzins", latest.sollzins_used, "%", 0.0001);
  }
  if (!touched.anschlusszins && latest.anschlusszins_used != null) {
    setControlDisplay("Anschlusszins", latest.anschlusszins_used, "%", 0.0001);
  }
  scenario.adults.forEach((adult, index) => {
    if (touched.pensions[adult.id]) return;
    const estimate = latest.pensions?.find((item) => item.id === adult.id)?.estimate;
    if (estimate == null) return;
    const name = adult.label || (index === 0 ? "Du" : "Zweite Person");
    setControlDisplay(`${name}: Rente brutto, Schätzung, Euro von heute`, estimate, "€", 10);
  });
}

const SLIDER_GROUP_ORDER = ["Arbeit", "Wohnen", "Kredit", "Vermögen", "Lebenslauf", "Rechnung"];

const BELIEF_SLIDER_GROUP = {
  rent_growth: "Wohnen",
  owner_cost_growth: "Wohnen",
  appreciation: "Wohnen",
  inflation: "Rechnung",
  etf_return: "Vermögen",
  ter: "Vermögen",
  basiszins: "Rechnung",
  tilgung: "Kredit",
  zinsbindung_years: "Kredit",
  sollzins: "Kredit",
  anschlusszins: "Kredit",
};

function emptySliderBuckets() {
  return Object.fromEntries(SLIDER_GROUP_ORDER.map((name) => [name, []]));
}

function captureSliderGroupState() {
  const host = document.getElementById("beliefs");
  if (!host) return { open: new Set(), scrollY: window.scrollY };
  const open = new Set();
  host.querySelectorAll("details.slider-group[open]").forEach((el) => {
    const title = el.querySelector(".slider-group-title span")?.textContent;
    if (title) open.add(title);
  });
  return { open, scrollY: window.scrollY };
}

function restoreSliderGroupState(state) {
  const host = document.getElementById("beliefs");
  if (!host || !state) return;
  host.querySelectorAll("details.slider-group").forEach((el) => {
    const title = el.querySelector(".slider-group-title span")?.textContent;
    if (title && state.open.has(title)) el.setAttribute("open", "");
  });
  window.scrollTo(0, state.scrollY);
}

function mountSliderGroups(host, buckets) {
  for (const title of SLIDER_GROUP_ORDER) {
    const items = buckets[title];
    if (!items.length) continue;
    const section = document.createElement("details");
    section.className = "slider-group";
    const heading = document.createElement("summary");
    heading.className = "slider-group-title";
    const titleText = document.createElement("span");
    titleText.textContent = title;
    heading.append(titleText);
    const grid = document.createElement("div");
    grid.className = "controls controls-compact";
    for (const node of items) grid.append(node);
    section.append(heading, grid);
    host.append(section);
  }
}

function defaultOwnerCostsRate() {
  const price = scenario.dwelling.purchase_price;
  if (!price) return 0.0075;
  const rate = scenario.dwelling.owner_costs_rate;
  if (Number.isFinite(rate)) return rate;
  const euros = scenario.dwelling.owner_costs;
  if (Number.isFinite(euros) && euros > 0) return (euros * 12) / price;
  return 0.0075;
}

function syncOwnerCostsFromRate(rate) {
  const price = scenario.dwelling.purchase_price;
  scenario.dwelling.owner_costs_rate = rate;
  if (price) scenario.dwelling.owner_costs = (price * rate) / 12;
}

function ensureOwnerCostsRate() {
  const rate = defaultOwnerCostsRate();
  syncOwnerCostsFromRate(rate);
  return rate;
}

function closeAllInfoTips() {
  document.querySelectorAll(".info-tip").forEach((node) => {
    node.hidden = true;
    node.style.position = "";
    node.style.left = "";
    node.style.top = "";
    node.style.width = "";
    node.style.maxWidth = "";
  });
}

function positionInfoTip(wrap, tip) {
  const margin = 10;
  const maxW = Math.min(288, window.innerWidth - margin * 2);
  const rect = wrap.getBoundingClientRect();
  let left = rect.left;
  if (left + maxW > window.innerWidth - margin) {
    left = window.innerWidth - margin - maxW;
  }
  left = Math.max(margin, left);
  tip.style.position = "fixed";
  tip.style.left = `${left}px`;
  tip.style.top = `${rect.bottom + 6}px`;
  tip.style.width = `${maxW}px`;
  tip.style.maxWidth = `${maxW}px`;
}

function infoButton(text) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "info-btn";
  button.setAttribute("aria-label", "Annahme");
  button.textContent = "i";
  const tip = document.createElement("span");
  tip.className = "info-tip";
  tip.hidden = true;
  tip.textContent = text;
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    const wasOpen = !tip.hidden;
    closeAllInfoTips();
    if (!wasOpen) {
      tip.hidden = false;
      positionInfoTip(wrap, tip);
    }
  });
  const wrap = document.createElement("span");
  wrap.className = "info-wrap";
  wrap.append(button, tip);
  return wrap;
}

window.addEventListener("resize", closeAllInfoTips);
document.addEventListener("scroll", closeAllInfoTips, true);

function assumptionLine(match) {
  const lines = latest?.assumptions || [];
  if (typeof match === "function") return match(lines);
  return lines.find((line) => line.includes(match)) || null;
}

function limitLines() {
  return latest?.limits || [];
}

function syncAssumptionInfos() {
  if (!latest) return;
  const matchers = [
    ["Brutto im Jahr", "Jede Person spart"],
    ["Bargeld außerhalb", "Zusätzliches Eigenkapital"],
    ["Depot nach der Rente", "Bei Erhalt"],
    [": Depot", "Die ETF-Depots"],
    ["Rente brutto", "Die gesetzliche Rente"],
    ["ETF-Rendite", "Die ETF-Rendite"],
    ["Mietsteigerung", "Die Mietsteigerung"],
    ["Inflation", "Die Inflation"],
    ["Wertsteigerung", "Die Wertsteigerung"],
    ["Notar", "Notar und Grundbuch"],
    ["Makler", "Makler, Käuferanteil"],
    ["Einmalige Einzugskosten", "Einmalige Einzugskosten"],
    ["Hausgeld", "Eigentümerkosten"],
    ["Eigenkapital vom Kaufpreis", "Gekauft wird erst"],
    ["Zuschlag größere", "Solange ein Weg noch mietet"],
    ["Eigenanteil Pflege", "Heiz- und andere Kosten"],
    ["Restvermögen am Horizont", "Bei vollem Verzehr"],
  ];
  document.querySelectorAll("#beliefs .control-label").forEach((caption) => {
    const label = caption.textContent || "";
    if (label.includes("Bargeld außerhalb")) {
      const text = assumptionLine("Zusätzliches Eigenkapital");
      if (!text) return;
      const tip = caption.querySelector(".info-tip");
      if (tip) {
        tip.textContent = text;
        return;
      }
      if (!caption.querySelector(".info-wrap")) caption.append(infoButton(text));
      return;
    }
    if (caption.querySelector(".info-wrap")) return;
    const hit = matchers.find(([prefix]) => label.includes(prefix));
    if (!hit) return;
    const text = assumptionLine(hit[1]);
    if (text) caption.append(infoButton(text));
  });
}

const BELIEFS = [
  ["rent_growth", "Mietsteigerung", 0, 0.08, 0.001, "%"],
  ["owner_cost_growth", "Steigerung Eigentümerkosten", 0, 0.08, 0.001, "%"],
  ["appreciation", "Wertsteigerung Haus oder Wohnung", -0.02, 0.12, 0.001, "%"],
  ["etf_return", "ETF-Rendite nominal, schon nach Quellensteuer", 0, 0.12, 0.001, "%"],
  ["ter", "TER", 0, 0.02, 0.0001, "%"],
  ["basiszins", "Basiszins Vorabpauschale", 0, 0.06, 0.0001, "%"],
  ["inflation", "Inflation", 0, 0.06, 0.001, "%"],
  ["tilgung", "Anfängliche Tilgung", 0, 0.1, 0.001, "%"],
  ["zinsbindung_years", "Zinsbindung in Jahren", 1, 30, 1, ""],
  ["sollzins", "Sollzins", 0, 0.1, 0.0001, "%"],
  ["anschlusszins", "Anschlusszins", 0, 0.1, 0.0001, "%"],
];

function coalesceNumber(value, fallback) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function clampSnap(value, min, max, step) {
  let v = Math.min(max, Math.max(min, value));
  if (step > 0) {
    v = Math.round(v / step) * step;
    const places = Math.max(0, -Math.floor(Math.log10(step)));
    v = Number(v.toFixed(places + 2));
    v = Math.min(max, Math.max(min, v));
  }
  return v;
}

function parseGermanNumber(raw) {
  let s = String(raw).trim().replace(/\u00a0/g, "").replace(/€/g, "").replace(/%/g, "").replace(/Jahre?/gi, "").trim();
  if (!s) return NaN;
  if (s.includes(",") && s.includes(".")) {
    s = s.replace(/\./g, "").replace(",", ".");
  } else if (s.includes(",")) {
    s = s.replace(",", ".");
  } else if (/\.\d{3}(?:\.\d{3})*$/.test(s)) {
    s = s.replace(/\./g, "");
  }
  const n = Number(s);
  return Number.isFinite(n) ? n : NaN;
}

function parseTypedValue(raw, unit, min, max) {
  const n = parseGermanNumber(raw);
  if (!Number.isFinite(n)) return NaN;
  if (unit === "%") {
    const hadPercent = /%/.test(String(raw));
    if (hadPercent || n > 1 || (max <= 1 && n > max)) return n / 100;
    return n;
  }
  if (unit === "years" || unit === "") return Math.round(n);
  return n;
}

function editTextForValue(value, unit, step) {
  if (!Number.isFinite(Number(value))) return "";
  if (unit === "%") {
    const pct = value * 100;
    const digits = percentDisplayDecimals(step ?? 0.001);
    return new Intl.NumberFormat("de-DE", {
      minimumFractionDigits: 0,
      maximumFractionDigits: digits,
    }).format(pct);
  }
  if (unit === "€") {
    return new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 }).format(value);
  }
  if (unit === "years") return String(Math.round(value));
  return String(Math.round(value));
}

function applySliderValue(range, out, unit, step, min, max, onInput, value) {
  const snapped = clampSnap(value, min, max, step);
  range.value = snapped;
  out.textContent = formatValue(snapped, unit, step);
  paintRange(range);
  onInput(snapped);
  schedule();
}

const DWELLING_DEFAULTS = {
  notary_rate: 0.02,
  broker_rate: 0.0357,
  selling_cost_rate: 0,
  owner_costs: 250,
  move_in_cost_2026: 0,
  owner_cost_growth: 0.02,
  appreciation: 0.025,
};

const BELIEF_DEFAULTS = {
  rent_growth: 0.025,
  owner_cost_growth: 0.02,
  appreciation: 0.025,
  etf_return: 0.087,
  ter: 0.0015,
  basiszins: 0.032,
  inflation: 0.02,
  etf_consume: 0,
  etf_reserve: 0,
  tilgung: 0.02,
  zinsbindung_years: 15,
  sollzins: 0,
  anschlusszins: 0,
};

function normalizeSliderScenario() {
  const d = scenario.dwelling;
  for (const [key, fallback] of Object.entries(DWELLING_DEFAULTS)) {
    const n = Number(d[key]);
    if (!Number.isFinite(n)) d[key] = fallback;
  }
  if (!Number.isFinite(Number(scenario.equity_cash))) scenario.equity_cash = 0;
  if (scenario.adults.length === 2 && !Number.isFinite(Number(scenario.shared_kaltmiete))) {
    scenario.shared_kaltmiete = 0;
  }
  if (!Number.isFinite(Number(d.min_equity_share))) d.min_equity_share = 0.15;
  ensureOwnerCostsRate();
  scenario.adults.forEach((adult) => {
    if (!Number.isFinite(Number(adult.gross_salary))) adult.gross_salary = 0;
    if (!Number.isFinite(Number(adult.depot))) adult.depot = 0;
    if (!Number.isFinite(Number(adult.sparrate))) adult.sparrate = 0;
    if (!Number.isFinite(Number(adult.kaltmiete))) adult.kaltmiete = 0;
    if (!Number.isFinite(Number(adult.retire_age))) adult.retire_age = 67;
    if (!Number.isFinite(Number(adult.care_age))) adult.care_age = 75;
    if (!Number.isFinite(Number(adult.salary_growth))) adult.salary_growth = 0.02;
    if (adult.church_tax == null) adult.church_tax = false;
    applyChurchTaxConsent(adult);
  });
  if (!scenario.beliefs) scenario.beliefs = {};
  for (const [key, fallback] of Object.entries(BELIEF_DEFAULTS)) {
    if (key === "sollzins" || key === "anschlusszins") continue;
    const slot = key === "owner_cost_growth" || key === "appreciation" ? d : scenario.beliefs;
    if (!Number.isFinite(Number(slot[key]))) slot[key] = fallback;
  }
}

function formatValue(value, unit, step) {
  if (!Number.isFinite(Number(value))) return "—";
  if (unit === "%") return formatPercent(value, step ?? 0.001);
  if (unit === "€") return euro.format(value);
  if (unit === "verzehr") return value <= 0 ? "Erhalt" : value >= 1 ? "auf Rest" : formatPercent(value, step ?? 0.05);
  if (unit === "years") return `${Math.round(value)} Jahre`;
  return String(Math.round(value));
}

function paintRange(range) {
  const min = Number(range.min);
  const max = Number(range.max);
  const portion = max === min ? 0 : ((Number(range.value) - min) / (max - min)) * 100;
  range.style.setProperty("--p", `${portion}%`);
}

function beliefValue(name) {
  if (name === "appreciation" || name === "owner_cost_growth") return scenario.dwelling[name];
  return scenario.beliefs[name];
}

function setBelief(name, value) {
  if (name === "appreciation" || name === "owner_cost_growth") scenario.dwelling[name] = value;
  else scenario.beliefs[name] = name === "zinsbindung_years" ? Math.round(value) : value;
  if (name === "sollzins") {
    touched.sollzins = true;
    if (!touched.anschlusszins) scenario.beliefs.anschlusszins = value;
  }
  if (name === "anschlusszins") touched.anschlusszins = true;
  if (name === "sollzins" || name === "anschlusszins") syncHeaderAdvice();
}

function slider(name, label, min, max, step, value, unit, onInput, infoText) {
  const wrap = document.createElement("div");
  wrap.className = "control";
  wrap.dataset.controlName = name;
  const caption = document.createElement("span");
  caption.className = "control-label";
  caption.textContent = label;
  if (infoText) caption.append(infoButton(infoText));
  const range = document.createElement("input");
  range.type = "range";
  range.min = min;
  range.max = max;
  range.step = step;
  const start = coalesceNumber(value, coalesceNumber(min, 0));
  range.value = start;
  range.setAttribute("aria-label", label);
  const out = document.createElement("output");
  out.textContent = formatValue(start, unit, step);
  out.tabIndex = 0;
  out.setAttribute("role", "textbox");
  out.setAttribute("aria-label", `${label}, Wert eingeben`);
  range.addEventListener("input", () => {
    const next = coalesceNumber(range.value, start);
    out.textContent = formatValue(next, unit, step);
    paintRange(range);
    onInput(next);
    schedule();
  });
  out.addEventListener("focus", () => {
    out.dataset.editing = "1";
    out.contentEditable = "true";
    const current = coalesceNumber(range.value, start);
    out.textContent = editTextForValue(current, unit, step);
    const selection = window.getSelection();
    const rangeDoc = document.createRange();
    rangeDoc.selectNodeContents(out);
    selection?.removeAllRanges();
    selection?.addRange(rangeDoc);
  });
  out.addEventListener("blur", () => {
    if (out.dataset.editing !== "1") return;
    delete out.dataset.editing;
    out.contentEditable = "false";
    const previous = coalesceNumber(range.value, start);
    const parsed = parseTypedValue(out.textContent, unit, min, max);
    if (!Number.isFinite(parsed)) {
      out.textContent = formatValue(previous, unit, step);
      return;
    }
    applySliderValue(range, out, unit, step, min, max, onInput, parsed);
  });
  out.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      out.blur();
    }
  });
  paintRange(range);
  wrap.append(caption, range, out);
  return wrap;
}

function mountBundeslandRow() {
  const row = document.createElement("div");
  row.className = "beliefs-bundesland";
  const label = document.createElement("span");
  label.textContent = "Bundesland";
  const select = document.createElement("select");
  select.setAttribute("aria-label", "Bundesland");
  bundeslaender.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    if (name === scenario.dwelling.bundesland) option.selected = true;
    select.append(option);
  });
  select.addEventListener("change", () => {
    scenario.dwelling.bundesland = select.value;
    schedule();
  });
  row.append(label, select);
  return row;
}

function mountEtfChoice(buckets) {
  const consume = scenario.beliefs.etf_consume ?? 0;
  const mixed = consume > 0 && consume < 1;
  const wrap = document.createElement("div");
  wrap.className = "control etf-choice";
  const caption = document.createElement("span");
  caption.className = "control-label";
  caption.textContent = "Depot nach der Rente";
  const holdInfo = assumptionLine("Bei Erhalt");
  const drawdownInfo = assumptionLine("Bei vollem Verzehr");
  if (holdInfo) caption.append(infoButton(holdInfo));
  const choices = document.createElement("div");
  choices.className = "choices etf-choices";
  const hold = document.createElement("button");
  hold.type = "button";
  hold.textContent = mixed ? "Mischung aus der Datei" : "Den Wert halten";
  hold.className = !mixed && consume <= 0 ? "primary" : "";
  const draw = document.createElement("button");
  draw.type = "button";
  draw.textContent = "Bis zum Ende abbauen";
  draw.className = !mixed && consume >= 1 ? "primary" : "";
  hold.addEventListener("click", () => {
    scenario.beliefs.etf_consume = 0;
    mountBeliefs();
    schedule();
  });
  draw.addEventListener("click", () => {
    scenario.beliefs.etf_consume = 1;
    mountBeliefs();
    schedule();
  });
  choices.append(hold, draw);
  wrap.append(caption, choices);
  buckets.Vermögen.push(wrap);
  if (!mixed && consume >= 1) {
    buckets.Vermögen.push(
      slider(
        "etf_reserve",
        "Restvermögen am Horizont, Euro von heute",
        0,
        5_000_000,
        10_000,
        scenario.beliefs.etf_reserve ?? 0,
        "€",
        (value) => {
          scenario.beliefs.etf_reserve = value;
        },
        drawdownInfo,
      ),
    );
  }
}

const AVD_POT_INFO =
  "Aus, bis der Schalter an ist. Dann 1.800 € eigene Beiträge im Jahr. Das holt die volle Grundzulage von 540 €. Die Kinderzulage ist darin schon bei 300 € je Kind voll. Der Stand wächst mit der ETF-Rendite. In der Sparphase keine Vorabpauschale.";

function ensureAdultPots(adult) {
  if (!adult.pots) adult.pots = {};
  const base = {
    capital_life: false,
    capital_life_balance: 0,
    capital_life_premiums: 0,
    private_lump: false,
    private_lump_balance: 0,
    private_lump_premiums: 0,
    private_annuity: false,
    private_annuity_balance: 0,
    private_annuity_yearly: 0,
    riester: false,
    riester_balance: 0,
    altersvorsorgedepot: false,
    altersvorsorgedepot_balance: 0,
    altersvorsorgedepot_contribution_yearly: 1800,
  };
  for (const [key, value] of Object.entries(base)) {
    if (adult.pots[key] === undefined) adult.pots[key] = value;
  }
}

const POT_SLIDER_SUFFIXES = {
  capital_life: ["capital_life_balance", "capital_life_premiums"],
  private_lump: ["private_lump_balance", "private_lump_premiums"],
  private_annuity: ["private_annuity_balance", "private_annuity_yearly"],
  riester: ["riester_balance"],
  altersvorsorgedepot: ["avd_balance", "avd_contrib"],
};

function syncParentMoneyVisibility() {
  const giftShow = Boolean(scenario?.parent_gift);
  const loanShow = Boolean(scenario?.parent_loan);
  const giftNode = document.querySelector(
    '#beliefs .control[data-control-name="parent_gift_amount"]',
  );
  const loanNode = document.querySelector(
    '#beliefs .control[data-control-name="parent_loan_amount"]',
  );
  const loanRateNode = document.querySelector(
    '#beliefs .control[data-control-name="parent_loan_rate"]',
    '#beliefs .control[data-control-name="parent_loan_tilgung"]',
  );
  if (giftNode) giftNode.hidden = !giftShow;
  if (loanNode) loanNode.hidden = !loanShow;
  if (loanRateNode) loanRateNode.hidden = !loanShow;
}

function ensureSharedHomeRent(dwelling) {
  if (!Array.isArray(dwelling.shared_home_rent)) dwelling.shared_home_rent = [];
  if (dwelling.shared_home_rent.length) dwelling.rent_while_living = true;
  const asOfYear = Number(String(scenario?.as_of ?? "2026-01-01").slice(0, 4)) || 2026;
  if (dwelling.rent_while_living && !dwelling.shared_home_rent.length) {
    dwelling.shared_home_rent = [
      {
        from: `${asOfYear}-01-01`,
        until: "2099-12-01",
        kalt: dwelling.rent_while_living_kalt ?? 600,
        payer: "stranger",
      },
    ];
  }
  if (!dwelling.rent_while_living) dwelling.shared_home_rent = [];
  for (const period of dwelling.shared_home_rent) {
    if (period.payer !== "spouse" && period.payer !== "stranger") period.payer = "stranger";
    if (period.kalt != null) dwelling.rent_while_living_kalt = period.kalt;
  }
}

function mountSharedHomePayerChoice(buckets, period, label, hidden) {
  const wrap = document.createElement("div");
  wrap.className = "control etf-choice";
  wrap.dataset.sharedHomeRentUi = "1";
  wrap.hidden = hidden;
  const caption = document.createElement("span");
  caption.className = "control-label";
  caption.textContent = label;
  const choices = document.createElement("div");
  choices.className = "choices etf-choices";
  const stranger = document.createElement("button");
  stranger.type = "button";
  stranger.textContent = "Fremder";
  stranger.className = period.payer !== "spouse" ? "primary" : "";
  const spouse = document.createElement("button");
  spouse.type = "button";
  spouse.textContent = "Ehepartner";
  spouse.className = period.payer === "spouse" ? "primary" : "";
  stranger.addEventListener("click", () => {
    period.payer = "stranger";
    mountBeliefs();
    schedule();
  });
  spouse.addEventListener("click", () => {
    period.payer = "spouse";
    mountBeliefs();
    schedule();
  });
  choices.append(stranger, spouse);
  wrap.append(caption, choices);
  buckets.Wohnen.push(wrap);
}

function syncRentWhileLivingVisibility() {
  const show = Boolean(scenario?.dwelling?.rent_while_living);
  document.querySelectorAll("[data-shared-home-rent-ui]").forEach((node) => {
    node.hidden = !show;
  });
}

function syncPotSliderVisibility() {
  if (!scenario?.adults) return;
  for (const adult of scenario.adults) {
    ensureAdultPots(adult);
    for (const [field, suffixes] of Object.entries(POT_SLIDER_SUFFIXES)) {
      const show = Boolean(adult.pots[field]);
      for (const suffix of suffixes) {
        const controlName = `pot-${adult.id}-${suffix}`;
        const node = document.querySelector(`#beliefs .control[data-control-name="${controlName}"]`);
        if (node) node.hidden = !show;
      }
    }
  }
}

function mountPotSwitch(buckets, adult, name, field, label, infoText) {
  ensureAdultPots(adult);
  const row = document.createElement("label");
  row.className = "switch belief-switch";
  const caption = document.createElement("span");
  caption.className = "switch-text";
  caption.textContent = `${label}: ${name}`;
  if (infoText) caption.append(infoButton(infoText));
  row.innerHTML = `<input type="checkbox" ${adult.pots[field] ? "checked" : ""}><span class="track"></span>`;
  row.append(caption);
  row.querySelector("input").addEventListener("change", (event) => {
    adult.pots[field] = event.target.checked;
    syncPotSliderVisibility();
    schedule();
  });
  buckets.Vermögen.push(row);
}

function mountAdultPots(buckets, adult, name) {
  ensureAdultPots(adult);
  const on = (field) => Boolean(adult.pots[field]);
  mountPotSwitch(buckets, adult, name, "capital_life", "Kapitallebensversicherung");
  buckets.Vermögen.push(
    slider(
      `pot-${adult.id}-capital_life_balance`,
      `${name}: Rückkaufswert Kapitallebensversicherung`,
      0,
      2_000_000,
      1_000,
      adult.pots.capital_life_balance,
      "€",
      (value) => {
        adult.pots.capital_life_balance = value;
      },
      null,
    ),
  );
  buckets.Vermögen[buckets.Vermögen.length - 1].hidden = !on("capital_life");
  buckets.Vermögen.push(
    slider(
      `pot-${adult.id}-capital_life_premiums`,
      `${name}: Beiträge Kapitallebensversicherung`,
      0,
      2_000_000,
      1_000,
      adult.pots.capital_life_premiums,
      "€",
      (value) => {
        adult.pots.capital_life_premiums = value;
      },
    ),
  );
  buckets.Vermögen[buckets.Vermögen.length - 1].hidden = !on("capital_life");
  mountPotSwitch(buckets, adult, name, "private_lump", "Private Einmalrente");
  buckets.Vermögen.push(
    slider(`pot-${adult.id}-private_lump_balance`, `${name}: Rückkaufswert Einmalrente`, 0, 2_000_000, 1_000, adult.pots.private_lump_balance, "€", (v) => {
      adult.pots.private_lump_balance = v;
    }),
    slider(`pot-${adult.id}-private_lump_premiums`, `${name}: Beiträge Einmalrente`, 0, 2_000_000, 1_000, adult.pots.private_lump_premiums, "€", (v) => {
      adult.pots.private_lump_premiums = v;
    }),
  );
  buckets.Vermögen[buckets.Vermögen.length - 2].hidden = !on("private_lump");
  buckets.Vermögen[buckets.Vermögen.length - 1].hidden = !on("private_lump");
  mountPotSwitch(buckets, adult, name, "private_annuity", "Private Leibrente");
  buckets.Vermögen.push(
    slider(`pot-${adult.id}-private_annuity_balance`, `${name}: Rückkaufswert Leibrente`, 0, 2_000_000, 1_000, adult.pots.private_annuity_balance, "€", (v) => {
      adult.pots.private_annuity_balance = v;
    }),
    slider(`pot-${adult.id}-private_annuity_yearly`, `${name}: Leibrente im Jahr`, 0, 200_000, 100, adult.pots.private_annuity_yearly, "€", (v) => {
      adult.pots.private_annuity_yearly = v;
    }),
  );
  buckets.Vermögen[buckets.Vermögen.length - 2].hidden = !on("private_annuity");
  buckets.Vermögen[buckets.Vermögen.length - 1].hidden = !on("private_annuity");
  mountPotSwitch(buckets, adult, name, "riester", "Riester bis 2026");
  buckets.Vermögen.push(
    slider(`pot-${adult.id}-riester_balance`, `${name}: Riester Rückkaufswert`, 0, 2_000_000, 1_000, adult.pots.riester_balance, "€", (v) => {
      adult.pots.riester_balance = v;
    }),
  );
  buckets.Vermögen[buckets.Vermögen.length - 1].hidden = !on("riester");
  mountPotSwitch(buckets, adult, name, "altersvorsorgedepot", "Altersvorsorgedepot ab 2027", AVD_POT_INFO);
  buckets.Vermögen.push(
    slider(`pot-${adult.id}-avd_balance`, `${name}: Altersvorsorgedepot Stand`, 0, 2_000_000, 1_000, adult.pots.altersvorsorgedepot_balance, "€", (v) => {
      adult.pots.altersvorsorgedepot_balance = v;
    }),
    slider(
      `pot-${adult.id}-avd_contrib`,
      `${name}: Eigene Beiträge Altersvorsorgedepot im Jahr`,
      0,
      10_000,
      50,
      adult.pots.altersvorsorgedepot_contribution_yearly,
      "€",
      (v) => {
        adult.pots.altersvorsorgedepot_contribution_yearly = v;
      },
    ),
  );
  buckets.Vermögen[buckets.Vermögen.length - 2].hidden = !on("altersvorsorgedepot");
  buckets.Vermögen[buckets.Vermögen.length - 1].hidden = !on("altersvorsorgedepot");
}

const CAREER_SLIDER_SUFFIXES = {
  job_change: ["job-year", "job-month", "job-gross", "job-growth"],
  unemployment: ["alg-year", "alg-month"],
};

function careerIsoStart(year, month) {
  return `${year}-${String(month).padStart(2, "0")}-01`;
}

function parseCareerStart(iso) {
  const text = String(iso || "2027-01-01").slice(0, 10);
  const [year, month] = text.split("-").map((part) => Number(part));
  return { year: year || 2027, month: month || 1 };
}

function syncCareerSliderVisibility(adult) {
  if (!adult.job_changes) adult.job_changes = [];
  if (!adult.unemployment) adult.unemployment = [];
  for (const [field, suffixes] of Object.entries(CAREER_SLIDER_SUFFIXES)) {
    const show = field === "job_change" ? adult.job_changes.length > 0 : adult.unemployment.length > 0;
    for (const suffix of suffixes) {
      const node = document.querySelector(`#beliefs .control[data-control-name="career-${adult.id}-${suffix}"]`);
      if (node) node.hidden = !show;
    }
  }
}

function mountCareerControls(buckets, adult, name) {
  if (!adult.job_changes) adult.job_changes = [];
  if (!adult.unemployment) adult.unemployment = [];
  const jobRow = document.createElement("label");
  jobRow.className = "switch belief-switch";
  jobRow.innerHTML = `<input type="checkbox" ${adult.job_changes.length ? "checked" : ""}><span class="track"></span><span class="switch-text">Jobwechsel: ${name}</span>`;
  jobRow.querySelector("input").addEventListener("change", (event) => {
    if (event.target.checked) {
      const start = careerIsoStart(scenario.as_of?.slice(0, 4) ?? 2027, Number(scenario.as_of?.slice(5, 7)) || 1);
      adult.job_changes = [{ start, gross_salary: adult.gross_salary, salary_growth: adult.salary_growth ?? 0.02 }];
    } else adult.job_changes = [];
    syncCareerSliderVisibility(adult);
    schedule();
  });
  buckets.Arbeit.push(jobRow);
  const jobStart = parseCareerStart(adult.job_changes[0]?.start);
  const jobGross = adult.job_changes[0]?.gross_salary ?? adult.gross_salary;
  const jobGrowth = adult.job_changes[0]?.salary_growth ?? adult.salary_growth ?? 0.02;
  buckets.Arbeit.push(
    slider(`career-${adult.id}-job-year`, `${name}: Jobwechsel Jahr`, 2000, 2100, 1, jobStart.year, "years", (value) => {
      const parsed = parseCareerStart(adult.job_changes[0]?.start);
      adult.job_changes = [{ start: careerIsoStart(Math.round(value), parsed.month), gross_salary: jobGross, salary_growth: jobGrowth }];
    }),
    slider(`career-${adult.id}-job-month`, `${name}: Jobwechsel Monat`, 1, 12, 1, jobStart.month, "years", (value) => {
      const parsed = parseCareerStart(adult.job_changes[0]?.start);
      adult.job_changes = [{ start: careerIsoStart(parsed.year, Math.round(value)), gross_salary: jobGross, salary_growth: jobGrowth }];
    }),
    slider(`career-${adult.id}-job-gross`, `${name}: Brutto nach Jobwechsel`, 0, 300_000, 1_000, jobGross, "€", (value) => {
      const parsed = parseCareerStart(adult.job_changes[0]?.start);
      adult.job_changes = [{ start: careerIsoStart(parsed.year, parsed.month), gross_salary: value, salary_growth: jobGrowth }];
    }),
    slider(`career-${adult.id}-job-growth`, `${name}: Wachstum nach Jobwechsel`, 0, 0.1, 0.001, jobGrowth, "%", (value) => {
      const parsed = parseCareerStart(adult.job_changes[0]?.start);
      adult.job_changes = [{ start: careerIsoStart(parsed.year, parsed.month), gross_salary: jobGross, salary_growth: value }];
    }),
  );
  const algRow = document.createElement("label");
  algRow.className = "switch belief-switch";
  algRow.innerHTML = `<input type="checkbox" ${adult.unemployment.length ? "checked" : ""}><span class="track"></span><span class="switch-text">Arbeitslosigkeit: ${name}</span>`;
  algRow.querySelector("input").addEventListener("change", (event) => {
    if (event.target.checked) {
      const start = careerIsoStart(scenario.as_of?.slice(0, 4) ?? 2027, Number(scenario.as_of?.slice(5, 7)) || 1);
      adult.unemployment = [{ start }];
    } else adult.unemployment = [];
    syncCareerSliderVisibility(adult);
    schedule();
  });
  buckets.Arbeit.push(algRow);
  const algStart = parseCareerStart(adult.unemployment[0]?.start);
  buckets.Arbeit.push(
    slider(`career-${adult.id}-alg-year`, `${name}: Arbeitslos ab Jahr`, 2000, 2100, 1, algStart.year, "years", (value) => {
      const parsed = parseCareerStart(adult.unemployment[0]?.start);
      adult.unemployment = [{ start: careerIsoStart(Math.round(value), parsed.month) }];
    }),
    slider(`career-${adult.id}-alg-month`, `${name}: Arbeitslos ab Monat`, 1, 12, 1, algStart.month, "years", (value) => {
      const parsed = parseCareerStart(adult.unemployment[0]?.start);
      adult.unemployment = [{ start: careerIsoStart(parsed.year, Math.round(value)) }];
    }),
  );
  syncCareerSliderVisibility(adult);
}

function mountBeliefs() {
  const groupState = captureSliderGroupState();
  const host = document.getElementById("beliefs");
  host.innerHTML = "";
  normalizeSliderScenario();
  if (scenario.beliefs?.church_tax) {
    scenario.adults.forEach((adult) => {
      if (adult.church_tax_consent) adult.church_tax = true;
    });
    scenario.beliefs.church_tax = false;
  }
  const buckets = emptySliderBuckets();
  const d = scenario.dwelling;
  const ownerRateShown = ensureOwnerCostsRate();
  scenario.adults.forEach((adult, index) => {
    const name = adult.label || (index === 0 ? "Du" : "Zweite Person");
    buckets.Arbeit.push(
      slider(`gross-${adult.id}`, `${name}: Brutto im Jahr`, 0, 300_000, 1_000, adult.gross_salary, "€", (value) => {
        adult.gross_salary = value;
      }, assumptionLine("Jede Person spart")),
      slider(`growth-${adult.id}`, `${name}: Gehaltswachstum`, 0, 0.1, 0.001, adult.salary_growth, "%", (value) => {
        adult.salary_growth = value;
      }),
    );
    mountCareerControls(buckets, adult, name);
  });
  scenario.adults.forEach((adult, index) => {
    const name = adult.label || (index === 0 ? "Du" : "Zweite Person");
    buckets.Wohnen.push(
      slider(`rent-${adult.id}`, `${name}: Kaltmiete`, 0, 5_000, 25, adult.kaltmiete, "€", (value) => {
        adult.kaltmiete = value;
      }),
    );
  });
  if (scenario.adults.length === 2) {
    buckets.Wohnen.push(
      slider("shared_kaltmiete", "Gemeinsame Kaltmiete", 0, 8_000, 25, scenario.shared_kaltmiete, "€", (value) => {
        scenario.shared_kaltmiete = value;
      }),
    );
  }
  if (scenario.extra_rent) {
    buckets.Wohnen.push(
      slider("extra_rent", "Zuschlag größere Wohnung", 0, 2_000, 25, scenario.extra_rent.amount_2026, "€", (value) => {
        scenario.extra_rent.amount_2026 = value;
      }, assumptionLine("Solange ein Weg noch mietet")),
    );
  }
  for (const [name, label, min, max, step, unit] of BELIEFS) {
    if (name === "rent_growth") {
      buckets.Wohnen.push(
        slider(name, label, min, max, step, beliefValue(name), unit, (value) => setBelief(name, value), assumptionLine("Die Mietsteigerung")),
      );
    }
  }
  buckets.Wohnen.push(
    slider("purchase_price", "Kaufpreis", 50_000, 2_000_000, 5_000, d.purchase_price, "€", (value) => {
      d.purchase_price = value;
      syncOwnerCostsFromRate(d.owner_costs_rate ?? ownerRateShown);
    }),
    mountBundeslandRow(),
    slider("notary_rate", "Notar und Grundbuch", 0, 0.1, 0.001, d.notary_rate, "%", (value) => {
      d.notary_rate = value;
    }, assumptionLine("Notar und Grundbuch")),
    slider("broker_rate", "Makler, Käuferanteil", 0, 0.1, 0.001, d.broker_rate, "%", (value) => {
      d.broker_rate = value;
    }, assumptionLine("Makler, Käuferanteil")),
    slider("selling_cost_rate", "Verkaufskosten", 0, 0.1, 0.001, d.selling_cost_rate, "%", (value) => {
      d.selling_cost_rate = value;
    }),
    slider("move_in_cost_2026", "Einmalige Einzugskosten", 0, 200_000, 500, d.move_in_cost_2026 || 0, "€", (value) => {
      d.move_in_cost_2026 = value;
    }, assumptionLine("Einmalige Einzugskosten")),
    slider(
      "owner_costs_rate",
      "Hausgeld, Anteil des Kaufpreises im Jahr",
      0,
      0.03,
      0.0005,
      ownerRateShown,
      "%",
      (value) => syncOwnerCostsFromRate(value),
      assumptionLine("Eigentümerkosten"),
    ),
  );
  if (d.rent_while_living == null) d.rent_while_living = false;
  if (d.rent_while_living_kalt == null) d.rent_while_living_kalt = 600;
  ensureSharedHomeRent(d);
  const rentLivingSwitch = document.createElement("label");
  rentLivingSwitch.className = "switch belief-switch";
  rentLivingSwitch.innerHTML = `<input type="checkbox" ${d.rent_while_living ? "checked" : ""}><span class="track"></span>`;
  const rentLivingCaption = document.createElement("span");
  rentLivingCaption.className = "switch-text";
  rentLivingCaption.textContent = "Kaltmiete im eigenen Haus";
  rentLivingSwitch.append(rentLivingCaption);
  rentLivingSwitch.querySelector("input").addEventListener("change", (event) => {
    d.rent_while_living = event.target.checked;
    if (!d.rent_while_living) d.shared_home_rent = [];
    ensureSharedHomeRent(d);
    mountBeliefs();
    schedule();
  });
  buckets.Wohnen.push(rentLivingSwitch);
  const addRentPhaseRow = document.createElement("div");
  addRentPhaseRow.className = "choices";
  addRentPhaseRow.dataset.sharedHomeRentUi = "1";
  addRentPhaseRow.hidden = !d.rent_while_living || d.shared_home_rent.length >= 8;
  const addRentPhase = document.createElement("button");
  addRentPhase.type = "button";
  addRentPhase.className = "quiet pill";
  addRentPhase.textContent = "Weitere Mietphase";
  addRentPhase.addEventListener("click", () => {
    ensureSharedHomeRent(d);
    if (d.shared_home_rent.length >= 8) return;
    const last = d.shared_home_rent.at(-1);
    const startYear = last ? Number(last.until.slice(0, 4)) + 1 : 2027;
    d.shared_home_rent.push({
      from: `${startYear}-01-01`,
      until: "2099-12-01",
      kalt: d.rent_while_living_kalt ?? 600,
      payer: "stranger",
    });
    mountBeliefs();
    schedule();
  });
  addRentPhaseRow.append(addRentPhase);
  buckets.Wohnen.push(addRentPhaseRow);
  d.shared_home_rent.forEach((period, index) => {
    const phaseNum = index + 1;
    const fromYear = Number(period.from.slice(0, 4));
    const untilYear = Number(period.until.slice(0, 4));
    const fromSlider = slider(
      `shared-home-rent-${index}-from`,
      `Mietphase ${phaseNum}: von Jahr`,
      2000,
      2100,
      1,
      fromYear,
      "years",
      (value) => {
        period.from = `${Math.round(value)}-01-01`;
      },
    );
    const untilSlider = slider(
      `shared-home-rent-${index}-until`,
      `Mietphase ${phaseNum}: bis Jahr`,
      2000,
      2100,
      1,
      untilYear,
      "years",
      (value) => {
        period.until = `${Math.round(value)}-12-01`;
      },
    );
    const kaltSlider = slider(
      `shared-home-rent-${index}-kalt`,
      `Mietphase ${phaseNum}: Kaltmiete im Monat`,
      0,
      10_000,
      50,
      period.kalt,
      "€",
      (value) => {
        period.kalt = value;
        d.rent_while_living_kalt = value;
      },
    );
    for (const node of [fromSlider, untilSlider, kaltSlider]) {
      node.dataset.sharedHomeRentUi = "1";
      node.hidden = !d.rent_while_living;
    }
    buckets.Wohnen.push(fromSlider, untilSlider, kaltSlider);
    mountSharedHomePayerChoice(
      buckets,
      period,
      `Mietphase ${phaseNum}: Zahler`,
      !d.rent_while_living,
    );
  });
  if (d.building_cost == null) d.building_cost = null;
  if (d.rented_area_share == null) d.rented_area_share = null;
  if (d.building_finished_year == null) d.building_finished_year = null;
  if (d.rented_maintenance_annual == null) d.rented_maintenance_annual = 0;
  if (d.modernization_cost == null) d.modernization_cost = 0;
  if (d.craftsman_labor_annual == null) d.craftsman_labor_annual = 0;
  const deductionSliders = [
    [
      "building_cost",
      "Gebäudewert ohne Grund",
      0,
      2_000_000,
      5_000,
      d.building_cost ?? 0,
      "€",
      (value) => {
        d.building_cost = value > 0 ? value : null;
      },
      assumptionLine("Abzüge bei Fremdmiete im eigenen Haus"),
    ],
    [
      "rented_area_share",
      "Vermieteter Anteil",
      0,
      1,
      0.01,
      d.rented_area_share ?? 0,
      "%",
      (value) => {
        d.rented_area_share = value > 0 ? value : null;
      },
    ],
    [
      "building_finished_year",
      "Fertigstellungsjahr",
      1900,
      2030,
      1,
      d.building_finished_year ?? 2000,
      "years",
      (value) => {
        d.building_finished_year = Math.round(value);
      },
    ],
    [
      "rented_maintenance_annual",
      "Erhaltung vermieteter Teil im Jahr",
      0,
      50_000,
      100,
      d.rented_maintenance_annual,
      "€",
      (value) => {
        d.rented_maintenance_annual = value;
      },
    ],
    [
      "modernization_cost",
      "Modernisierung nach Kauf",
      0,
      500_000,
      1_000,
      d.modernization_cost,
      "€",
      (value) => {
        d.modernization_cost = value;
      },
    ],
    [
      "craftsman_labor_annual",
      "Handwerker im Eigenteil im Jahr",
      0,
      20_000,
      100,
      d.craftsman_labor_annual,
      "€",
      (value) => {
        d.craftsman_labor_annual = value;
      },
      assumptionLine("Handwerker im Eigenteil"),
    ],
  ];
  for (const row of deductionSliders) {
    const [name, label, min, max, step, start, unit, onChange, assumption] = row;
    const node = slider(name, label, min, max, step, start, unit, onChange, assumption);
    node.dataset.sharedHomeRentUi = "1";
    node.hidden = !d.rent_while_living;
    buckets.Wohnen.push(node);
  }
  for (const [name, label, min, max, step, unit] of BELIEFS) {
    if (name === "owner_cost_growth") {
      buckets.Wohnen.push(
        slider(name, label, min, max, step, beliefValue(name), unit, (value) => setBelief(name, value), assumptionLine("Eigentümerkosten")),
      );
    } else if (name === "appreciation") {
      buckets.Wohnen.push(
        slider(name, label, min, max, step, beliefValue(name), unit, (value) => setBelief(name, value), assumptionLine("Die Wertsteigerung")),
      );
    }
  }
  scenario.adults.forEach((adult, index) => {
    const name = adult.label || (index === 0 ? "Du" : "Zweite Person");
    buckets.Lebenslauf.push(
      slider(`retire-${adult.id}`, `${name}: Rentenalter`, 55, 75, 1, adult.retire_age, "years", (value) => {
        adult.retire_age = Math.round(value);
      }),
    );
    const pension =
      adult.pension_gross_today ??
      latest?.pensions?.find((item) => item.id === adult.id)?.estimate ??
      0;
    const pensionLabel =
      touched.pensions[adult.id] || adult.pension_gross_today != null
        ? `${name}: Rente brutto, Euro von heute`
        : `${name}: Rente brutto, Schätzung, Euro von heute`;
    buckets.Lebenslauf.push(
      slider(`pension-${adult.id}`, pensionLabel, 0, 6000, 10, pension, "€", (value) => {
        touched.pensions[adult.id] = true;
        adult.pension_gross_today = value;
      }, assumptionLine("Die gesetzliche Rente")),
      slider(`care-${adult.id}`, `${name}: Pflegealter`, 60, 95, 1, adult.care_age, "years", (value) => {
        adult.care_age = Math.round(value);
      }),
    );
  });
  const horizonAge = scenario.horizon?.age ?? 100;
  buckets.Lebenslauf.push(
    slider("horizon_age", "Alter am Ende der Rechnung", 50, 110, 1, horizonAge, "years", (value) => {
      if (!scenario.horizon) {
        const younger = scenario.adults.reduce((best, adult) => (adult.birth > best.birth ? adult : best));
        scenario.horizon = { adult_id: younger.id, age: Math.round(value) };
      } else scenario.horizon.age = Math.round(value);
    }),
  );
  scenario.adults.forEach((adult, index) => {
    const name = adult.label || (index === 0 ? "Du" : "Zweite Person");
    buckets.Vermögen.push(
      slider(`depot-${adult.id}`, `${name}: Depot`, 0, 500_000, 1_000, adult.depot, "€", (value) => {
        adult.depot = value;
      }, assumptionLine("Die ETF-Depots")),
      slider(`spar-${adult.id}`, `${name}: Sparrate im Monat`, 0, 10_000, 50, adult.sparrate, "€", (value) => {
        adult.sparrate = value;
      }),
    );
    mountAdultPots(buckets, adult, name);
  });
  buckets.Vermögen.push(
    slider("equity_cash", "Bargeld außerhalb des Depots", 0, 500_000, 1_000, scenario.equity_cash, "€", (value) => {
      scenario.equity_cash = value;
    }, assumptionLine("Zusätzliches Eigenkapital")),
  );
  if (scenario.parent_gift == null) scenario.parent_gift = false;
  if (scenario.parent_gift_amount == null) scenario.parent_gift_amount = 0;
  if (scenario.parent_loan == null) scenario.parent_loan = false;
  if (scenario.parent_loan_amount == null) scenario.parent_loan_amount = 0;
  if (!Number.isFinite(Number(scenario.parent_loan_rate))) scenario.parent_loan_rate = 0;
  if (!Number.isFinite(Number(scenario.parent_loan_tilgung))) scenario.parent_loan_tilgung = 0;
  const giftSwitch = document.createElement("label");
  giftSwitch.className = "switch belief-switch";
  giftSwitch.innerHTML = `<input type="checkbox" ${scenario.parent_gift ? "checked" : ""}><span class="track"></span>`;
  const giftCaption = document.createElement("span");
  giftCaption.className = "switch-text";
  giftCaption.textContent = "Schenkung der Eltern";
  giftSwitch.append(giftCaption);
  giftSwitch.querySelector("input").addEventListener("change", (event) => {
    scenario.parent_gift = event.target.checked;
    syncParentMoneyVisibility();
    schedule();
  });
  buckets.Vermögen.push(giftSwitch);
  buckets.Vermögen.push(
    slider(
      "parent_gift_amount",
      "Schenkung der Eltern, ein Betrag",
      0,
      2_000_000,
      1_000,
      scenario.parent_gift_amount,
      "€",
      (value) => {
        scenario.parent_gift_amount = value;
      },
    ),
  );
  buckets.Vermögen[buckets.Vermögen.length - 1].hidden = !scenario.parent_gift;
  const loanSwitch = document.createElement("label");
  loanSwitch.className = "switch belief-switch";
  loanSwitch.innerHTML = `<input type="checkbox" ${scenario.parent_loan ? "checked" : ""}><span class="track"></span>`;
  const loanCaption = document.createElement("span");
  loanCaption.className = "switch-text";
  loanCaption.textContent = "Darlehen der Eltern";
  loanSwitch.append(loanCaption);
  loanSwitch.querySelector("input").addEventListener("change", (event) => {
    scenario.parent_loan = event.target.checked;
    syncParentMoneyVisibility();
    schedule();
  });
  buckets.Vermögen.push(loanSwitch);
  buckets.Vermögen.push(
    slider(
      "parent_loan_amount",
      "Darlehen der Eltern, Betrag",
      0,
      2_000_000,
      1_000,
      scenario.parent_loan_amount,
      "€",
      (value) => {
        scenario.parent_loan_amount = value;
      },
    ),
  );
  buckets.Vermögen[buckets.Vermögen.length - 1].hidden = !scenario.parent_loan;
  buckets.Vermögen.push(
    slider(
      "parent_loan_rate",
      "Darlehen der Eltern, Zinssatz im Jahr",
      0,
      0.15,
      0.001,
      scenario.parent_loan_rate,
      "%",
      (value) => {
        scenario.parent_loan_rate = value;
      },
      assumptionLine("Zins auf Darlehen der Eltern"),
    ),
  );
  buckets.Vermögen[buckets.Vermögen.length - 1].hidden = !scenario.parent_loan;
  buckets.Vermögen.push(
    slider(
      "parent_loan_tilgung",
      "Darlehen der Eltern, Tilgung im Jahr",
      0,
      0.1,
      0.001,
      scenario.parent_loan_tilgung,
      "%",
      (value) => {
        scenario.parent_loan_tilgung = value;
      },
      assumptionLine("Tilgung, Darlehen der Eltern"),
    ),
  );
  buckets.Vermögen[buckets.Vermögen.length - 1].hidden = !scenario.parent_loan;
  const household = document.createElement("label");
  household.className = "switch belief-switch";
  household.innerHTML = `<input type="checkbox" ${scenario.beliefs.household_rate !== false ? "checked" : ""}><span class="track"></span><span class="switch-text">Zins nach der Haushaltslage</span>`;
  household.querySelector("input").addEventListener("change", (event) => {
    scenario.beliefs.household_rate = event.target.checked;
    if (!touched.sollzins) scenario.beliefs.sollzins = null;
    schedule();
  });
  buckets.Kredit.push(household);
  for (const [name, label, min, max, step, unit] of BELIEFS) {
    if (name === "etf_return") {
      buckets.Vermögen.push(
        slider(name, label, min, max, step, beliefValue(name), unit, (value) => setBelief(name, value), assumptionLine("Die ETF-Rendite")),
      );
      continue;
    }
    if (name === "ter") {
      buckets.Vermögen.push(slider(name, label, min, max, step, beliefValue(name), unit, (value) => setBelief(name, value)));
      continue;
    }
    if (name === "rent_growth" || name === "inflation" || name === "owner_cost_growth" || name === "appreciation") {
      continue;
    }
    if (name === "basiszins") continue;
    const current = beliefValue(name);
    const shown =
      current == null
        ? name === "sollzins"
          ? latest?.sollzins_used
          : name === "anschlusszins"
            ? latest?.anschlusszins_used
            : BELIEF_DEFAULTS[name]
        : current;
    const group = BELIEF_SLIDER_GROUP[name] || "Rechnung";
    buckets[group].push(slider(name, label, min, max, step, shown, unit, (value) => setBelief(name, value)));
  }
  mountEtfChoice(buckets);
  const equity = document.createElement("label");
  equity.className = "switch belief-switch";
  equity.innerHTML = `<input type="checkbox" ${scenario.dwelling.min_equity ? "checked" : ""}><span class="track"></span><span class="switch-text">Erst kaufen, wenn Nebenkosten und Eigenkapitalanteil gedeckt sind</span>`;
  equity.querySelector("input").addEventListener("change", (event) => {
    scenario.dwelling.min_equity = event.target.checked;
    schedule();
  });
  buckets.Wohnen.push(equity);
  buckets.Wohnen.push(
    slider(
      "min_equity_share",
      "Eigenkapital vom Kaufpreis vor dem Kauf",
      0,
      0.5,
      0.01,
      d.min_equity_share ?? 0.15,
      "%",
      (value) => {
        d.min_equity_share = value;
      },
      assumptionLine("Gekauft wird erst, wenn Depot und zusätzliches Eigenkapital"),
    ),
  );
  buckets.Lebenslauf.push(
    slider(
      "care_copay",
      "Eigenanteil Pflege, Euro von 2026",
      0,
      15_000,
      100,
      scenario.care_copay_2026 ?? 5_800,
      "€",
      (value) => {
        scenario.care_copay_2026 = value <= 0 ? null : value;
      },
      assumptionLine("Heiz- und andere Kosten"),
    ),
  );
  scenario.adults.forEach((adult, index) => {
    const name = adult.label || (index === 0 ? "Du" : "Zweite Person");
    const block = document.createElement("div");
    block.className = "church-tax-block";
    const consent = document.createElement("label");
    consent.className = "church-consent";
    consent.innerHTML = `<input type="checkbox" ${adult.church_tax_consent ? "checked" : ""}><span>${churchTaxConsentLabel(name)}</span>`;
    const consentInput = consent.querySelector("input");
    const church = document.createElement("label");
    church.className = "switch belief-switch";
    church.innerHTML = `<input type="checkbox" ${adult.church_tax ? "checked" : ""} ${adult.church_tax_consent ? "" : "disabled"}><span class="track"></span><span class="switch-text">Kirchensteuer in der Rechnung: ${name}</span>`;
    const switchInput = church.querySelector("input");
    consentInput.addEventListener("change", (event) => {
      adult.church_tax_consent = event.target.checked;
      applyChurchTaxConsent(adult);
      switchInput.disabled = !adult.church_tax_consent;
      switchInput.checked = adult.church_tax;
      schedule();
    });
    switchInput.addEventListener("change", (event) => {
      if (!adult.church_tax_consent) {
        event.target.checked = false;
        return;
      }
      adult.church_tax = event.target.checked;
      schedule();
    });
    block.append(consent, church);
    buckets.Rechnung.push(block);
  });
  for (const [name, label, min, max, step, unit] of BELIEFS) {
    if (name === "inflation") {
      buckets.Rechnung.push(
        slider(name, label, min, max, step, beliefValue(name), unit, (value) => setBelief(name, value), assumptionLine("Die Inflation")),
      );
    }
  }
  buckets.Rechnung.push(
    slider("basiszins", "Basiszins Vorabpauschale", 0, 0.06, 0.0001, beliefValue("basiszins"), "%", (value) => setBelief("basiszins", value)),
  );
  mountSliderGroups(host, buckets);
  restoreSliderGroupState(groupState);
  syncPotSliderVisibility();
  syncRentWhileLivingVisibility();
  syncParentMoneyVisibility();
}

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(run, 200);
}

const COMPARE_COUNT_HEADER = "X-Buy-Vs-Rent-Count";

async function run(options = {}) {
  const id = ++requestId;
  const body = structuredClone(scenario);
  if (!touched.sollzins) body.beliefs.sollzins = null;
  if (!touched.anschlusszins) body.beliefs.anschlusszins = null;
  for (const adult of body.adults) {
    if (!touched.pensions[adult.id]) adult.pension_gross_today = null;
    applyChurchTaxConsent(adult);
  }
  const headers = { "Content-Type": "application/json" };
  if (options.countRechnen) headers[COMPARE_COUNT_HEADER] = "chat";
  const response = await fetch("/api/compare", {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!response.ok || id !== requestId) {
    if (id === requestId) {
      const err = document.getElementById("compare-error");
      if (err) {
        const payload = await response.json().catch(() => ({}));
        err.textContent =
          payload.detail || "Die Eingaben sind unvollständig oder ungültig.";
      }
    }
    return;
  }
  latest = await response.json();
  if (!touched.sollzins) scenario.beliefs.sollzins = null;
  renderResult(latest);
  syncSaveRowButton();
  syncBeliefDisplays();
  syncHeaderAdvice();
  syncAssumptionInfos();
  syncPurchasePriceInfo();
}

async function loadBundeslaender() {
  try {
    const defaults = await fetch("/api/defaults").then((response) => response.json());
    bundeslaender = Object.keys(defaults.bundeslaender || {}).sort();
  } catch {
    bundeslaender = ["Bayern"];
  }
}

async function showScenario(next, demo) {
  scenario = next;
  if (!scenario.path_scope) scenario.path_scope = "both";
  applyPathScopeFromScenario(scenario);
  if (scenario.dwelling.move_in_cost_2026 == null) scenario.dwelling.move_in_cost_2026 = 0;
  if (!scenario.beliefs) scenario.beliefs = {};
  touched.sollzins = scenario.beliefs.sollzins != null;
  touched.anschlusszins = scenario.beliefs.anschlusszins != null;
  touched.pensions = {};
  document.getElementById("banner").hidden = !demo;
  document.getElementById("gate").hidden = true;
  document.getElementById("chat").hidden = true;
  document.getElementById("results").hidden = false;
  window.syncStartScreen?.();
  await loadBundeslaender();
  snapshotFromScenario();
  horizonMonthYear = null;
  mountBeliefs();
  syncSaveRowButton();
  run();
}

window.showScenario = showScenario;

document.getElementById("edit")?.addEventListener("click", () => window.reopenChat(scenario));
document.getElementById("gate-choice")?.addEventListener("click", () => {
  const body = structuredClone(scenario);
  if (!touched.sollzins) body.beliefs.sollzins = null;
  if (!touched.anschlusszins) body.beliefs.anschlusszins = null;
  for (const adult of body.adults) {
    if (!touched.pensions[adult.id]) adult.pension_gross_today = null;
    applyChurchTaxConsent(adult);
  }
  window.scenarioStore.saveOpenRow(body);
  document.getElementById("banner").hidden = true;
  window.showGate();
});
document.getElementById("save-row")?.addEventListener("click", () => {
  if (!window.scenarioStore.saveOpenRow(scenario)) return;
  snapshotFromScenario();
});
document.getElementById("reset")?.addEventListener("click", () => {
  if (!scenarioSnapshot) return;
  scenario = structuredClone(scenarioSnapshot);
  touched.sollzins = touchedSnapshot?.sollzins ?? false;
  touched.anschlusszins = touchedSnapshot?.anschlusszins ?? false;
  touched.pensions = { ...(touchedSnapshot?.pensions || {}) };
  mountBeliefs();
  run();
});
document.getElementById("export")?.addEventListener("click", () => window.scenarioStore.downloadScenario(scenario));
document.getElementById("import")?.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  event.target.value = "";
  if (!file) return;
  const loaded = await window.scenarioStore.readScenarioFile(file);
  window.scenarioStore.addRow(loaded);
  window.showGate();
});
document.getElementById("real")?.addEventListener("change", () => latest && renderResult(latest));

let beliefSearchFlashTimer = 0;

function runBeliefSearch() {
  const input = document.getElementById("beliefs-search");
  const hint = document.getElementById("beliefs-search-hint");
  const beliefsRoot = document.getElementById("beliefs");
  if (!input || !beliefsRoot || !window.BeliefSearch) return;
  const query = input.value;
  document.querySelectorAll("#beliefs .control.belief-search-hit").forEach((node) => {
    node.classList.remove("belief-search-hit");
  });
  const controls = window.BeliefSearch.findBeliefControls(beliefsRoot, query);
  if (!controls.length) {
    if (hint) {
      hint.hidden = !query.trim();
      hint.textContent = query.trim() ? "Kein passender Schieberegler." : "";
    }
    return;
  }
  if (hint) {
    hint.hidden = true;
    hint.textContent = "";
  }
  for (const control of controls) {
    control.closest("details.slider-group")?.setAttribute("open", "");
    control.classList.add("belief-search-hit");
  }
  controls[0].scrollIntoView({ behavior: "smooth", block: "nearest" });
  const range = controls[0].querySelector('input[type="range"]');
  range?.focus({ preventScroll: true });
  clearTimeout(beliefSearchFlashTimer);
  beliefSearchFlashTimer = window.setTimeout(() => {
    document.querySelectorAll("#beliefs .control.belief-search-hit").forEach((node) => {
      node.classList.remove("belief-search-hit");
    });
  }, 2400);
}

document.getElementById("beliefs-search")?.addEventListener("search", runBeliefSearch);
document.getElementById("beliefs-search")?.addEventListener("change", runBeliefSearch);
document.getElementById("beliefs-search")?.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    runBeliefSearch();
  }
});

function syncPathViewUi() {
  const results = document.getElementById("results");
  if (results) results.dataset.pathView = pathView;
  const completeRent = document.getElementById("complete-rent");
  const completeBuy = document.getElementById("complete-buy");
  const scope = scenario?.path_scope || "both";
  if (completeRent) completeRent.hidden = scope !== "buy";
  if (completeBuy) completeBuy.hidden = scope !== "rent";
  const legend = document.getElementById("wealth-legend");
  if (legend) {
    if (pathView === "buy") {
      legend.innerHTML =
        '<span class="swatch buy"></span>Kaufen <span class="swatch etf"></span>ETF im Kauf';
    } else if (pathView === "rent") {
      legend.innerHTML = '<span class="swatch rent"></span>Mieten';
    } else {
      legend.innerHTML =
        '<span class="swatch buy"></span>Kaufen <span class="swatch etf"></span>ETF im Kauf <span class="swatch rent"></span>Mieten';
    }
  }
}

document.getElementById("complete-rent")?.addEventListener("click", () => window.openPathCompletion("rent", scenario));
document.getElementById("complete-buy")?.addEventListener("click", () => window.openPathCompletion("buy", scenario));
function gapTone(buy, rent) {
  const gap = buy - rent;
  if (Math.abs(gap) < 1) return "tie";
  return gap > 0 ? "buy" : "rent";
}

function summaryAmount(value) {
  return axisAmount(value).replace(/ Tsd\. €/g, "\u00a0Tsd.\u00a0€").replace(/ Mio\. €/g, "\u00a0Mio.\u00a0€");
}

function gapLimitInfo() {
  const limits = limitLines();
  return limits.slice(1, 3).filter(Boolean).join(" ");
}

function factorBandInfo(result) {
  return (result.assumptions || []).find((line) => line.includes("Kaufpreisfaktor")) || "Unter 20, 20 bis 25 und über 25 sind keine Empfehlung.";
}

function purchasePriceInfo(result) {
  const formula = factorBandInfo(result);
  const interest = `Zinsen über die Laufzeit: ${summaryAmount(result.interest_paid || 0)}.`;
  if (result.price_to_rent == null) {
    return `${formula} Im Startmonat gibt es keine Vergleichskaltmiete. ${interest}`;
  }
  const shown = result.price_to_rent.toLocaleString("de-DE", { maximumFractionDigits: 1 });
  return (
    `Kaufpreisfaktor ${shown} (${result.price_to_rent_band}). ` +
    `Kaufpreis geteilt durch zwölf Monate Vergleichskaltmiete in Euro von heute. ` +
    `Ein Zuschlag für eine größere Wohnung zählt nicht. ${formula} ${interest}`
  );
}

function syncPurchasePriceInfo() {
  if (!latest) return;
  const caption = document.querySelector('[data-control-name="purchase_price"] .control-label');
  if (!caption) return;
  const text = purchasePriceInfo(latest);
  const tip = caption.querySelector(".info-tip");
  if (tip) {
    tip.textContent = text;
    return;
  }
  caption.append(infoButton(text));
}

function gapText(buy, rent) {
  const gap = buy - rent;
  if (Math.abs(gap) < 1) return "gleich";
  const ahead = gap > 0 ? "buy" : "rent";
  const label = gap > 0 ? "Kaufen" : "Mieten";
  const base = gap > 0 ? rent : buy;
  const ratio = base > 1 ? (gap > 0 ? buy / rent : rent / buy) : null;
  const factor =
    ratio == null
      ? ""
      : ` · ${ratio.toLocaleString("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}×`;
  return `<span class="gap-${ahead}">${label}</span> +${summaryAmount(Math.abs(gap))}${factor}`;
}

function gapLineHtml(buy, rent) {
  return `<p class="hero-gap path-both-only delta ${gapTone(buy, rent)}"><span class="hero-gap-side" aria-hidden="true"></span><span class="hero-gap-text">${gapText(buy, rent)}</span><span class="hero-gap-side hero-gap-side-end" aria-hidden="true"></span></p>`;
}

function renderResult(result) {
  const real = document.getElementById("real").checked;
  const buy = real ? result.buy_final_real : result.buy_final_nominal;
  const rent = real ? result.rent_final_real : result.rent_final_nominal;
  let careBuy = result.care_buy_real;
  let careRent = result.care_rent_real;
  if (!real && result.care_start && result.series?.length) {
    const careMonth = result.care_start.slice(0, 7);
    const point =
      result.series.find((item) => item.date.slice(0, 7) === careMonth) ||
      result.series.find((item) => item.date >= result.care_start);
    if (point) {
      careBuy = point.buy_nominal;
      careRent = point.rent_nominal;
    }
  }
  document.getElementById("results").hidden = false;
  const compareError = document.getElementById("compare-error");
  if (compareError) compareError.textContent = "";
  const gapInfo = gapLimitInfo();
  document.getElementById("figures").innerHTML = `
    <div class="hero-grid">
      <article class="hero buy path-buy-only"><span>Kaufen</span><strong>${summaryAmount(buy)}</strong></article>
      ${gapLineHtml(buy, rent)}
      <article class="hero rent path-rent-only"><span>Mieten</span><strong>${summaryAmount(rent)}</strong></article>
    </div>
  `;
  const gapSide = document.querySelector("#figures .hero-gap-side-end");
  if (gapSide && gapInfo) gapSide.append(infoButton(gapInfo));
  const gaps = document.getElementById("life-gaps");
  if (careBuy != null && careRent != null) {
    gaps.innerHTML = `
      <p class="care-label totals-accent-label">Bei Pflegebeginn</p>
      <div class="hero-grid care-compact">
        <article class="hero buy path-buy-only"><span>Kaufen</span><strong>${summaryAmount(careBuy)}</strong></article>
        ${gapLineHtml(careBuy, careRent)}
        <article class="hero rent path-rent-only"><span>Mieten</span><strong>${summaryAmount(careRent)}</strong></article>
      </div>`;
  } else {
    gaps.innerHTML = "";
  }
  const life = document.getElementById("life-sentence");
  if (life) life.replaceChildren();
  const factorInterest = document.getElementById("factor-interest");
  if (factorInterest) factorInterest.replaceChildren();
  syncPurchasePriceInfo();
  renderHorizonMonth(result, real);
  syncPathViewUi();
  document.getElementById("warnings").innerHTML = result.warnings.map((item) => `<li>${item}</li>`).join("");
  drawWealth(result.series, real, result.markers);
  drawLoan(result.series, result.markers);
  drawFlows(result.cashflow || [], real, result.markers);
}

function drawWealth(series, real, markers) {
  const buyKey = real ? "buy_real" : "buy_nominal";
  const rentKey = real ? "rent_real" : "rent_nominal";
  const etfKey = real ? "buy_etf_real" : "buy_etf_nominal";
  let specs = [
    [buyKey, "buy"],
    [rentKey, "rent"],
    [etfKey, "etf"],
  ];
  if (pathView === "buy") specs = [[buyKey, "buy"], [etfKey, "etf"]];
  if (pathView === "rent") specs = [[rentKey, "rent"]];
  const values = series.flatMap((point) => specs.map(([key]) => point[key]));
  paintChart(document.getElementById("wealth"), series, specs, values, 210, "wealth", markers);
}

function drawLoan(series, markers) {
  const values = series.map((point) => point.loan_balance);
  paintChart(document.getElementById("loan"), series, [["loan_balance", "loan"]], values, 150, "loan", markers);
}

const RENT_FLOW = [
  ["rent_housing", "Miete", RENT_COLOR],
  ["rent_etf", "ETF", RENT_ETF_COLOR],
  ["rent_left", "Übrig", "#94a3b8"],
];
const BUY_FLOW = [
  ["buy_rent", "Miete", RENT_COLOR],
  ["buy_interest", "Zinsen", "#c2410c"],
  ["buy_principal", "Tilgung", BUY_COLOR],
  ["buy_owner", "Eigentümerkosten", "#d97706"],
  ["buy_etf", "ETF", BUY_ETF_COLOR],
  ["buy_left", "Übrig", "#94a3b8"],
];
const HORIZON_MONTH_BUY = [
  ["buy_living_rent", "Kaltmiete im eigenen Haus"],
  ["buy_interest", "Zinsen"],
  ["buy_principal", "Tilgung"],
  ["buy_owner", "Eigentümerkosten"],
  ["buy_etf", "ETF"],
  ["buy_left", "Übrig"],
];
const HORIZON_MONTH_RENT = [
  ["rent_housing", "Miete"],
  ["rent_etf", "ETF"],
  ["rent_left", "Übrig"],
];

function horizonMonthPoint(cashflow, purchaseDate) {
  if (!cashflow?.length) return null;
  const anchor = purchaseDate || cashflow[0].date;
  return cashflow.find((point) => point.date >= anchor) ?? cashflow.at(-1);
}

function cashflowYears(cashflow) {
  return [...new Set(cashflow.map((point) => point.date.slice(0, 4)))].sort();
}

function horizonMonthPointForYear(cashflow, year) {
  return cashflow.find((point) => point.date.startsWith(year)) ?? null;
}

function defaultHorizonMonthYear(cashflow, purchaseDate) {
  const point = horizonMonthPoint(cashflow, purchaseDate);
  return point ? point.date.slice(0, 4) : cashflow[0].date.slice(0, 4);
}

function bindHorizonMonthYear() {
  if (horizonMonthYearBound) return;
  const select = document.getElementById("horizon-month-year");
  if (!select) return;
  horizonMonthYearBound = true;
  select.addEventListener("change", () => {
    horizonMonthYear = select.value;
    if (latest) {
      renderHorizonMonth(latest, document.getElementById("real")?.checked ?? true);
    }
  });
}

function horizonMonthRows(point, layers, real) {
  const rows = layers
    .map(([key, label]) => {
      const value = flowAmount(point, key, real);
      if (!FLOW_LEFT_KEYS.has(key) && value <= 1) return "";
      const warn = FLOW_LEFT_KEYS.has(key) && value < -1;
      const ubrigClass = FLOW_LEFT_KEYS.has(key) ? "horizon-month-ubrig" : "";
      const warnClass = warn ? " flow-ubrig-warn" : "";
      const classAttr = ubrigClass || warnClass ? ` class="${ubrigClass}${warnClass}"` : "";
      return `<li><span class="horizon-month-label">${label}</span><strong${classAttr}>${euro.format(value)}</strong></li>`;
    })
    .filter(Boolean);
  const drawKey = layers === HORIZON_MONTH_BUY ? "buy_draw" : "rent_draw";
  const draw = flowAmount(point, drawKey, real);
  if (draw > 150) {
    rows.push(
      `<li><span class="horizon-month-label">ETF-Entnahme</span><strong>${euro.format(draw)}</strong></li>`,
    );
  }
  return rows.join("");
}

function renderHorizonMonth(result, real) {
  const section = document.getElementById("horizon-month");
  const buyList = document.getElementById("horizon-month-buy");
  const rentList = document.getElementById("horizon-month-rent");
  const yearSelect = document.getElementById("horizon-month-year");
  if (!section || !buyList || !rentList || !yearSelect) return;
  bindHorizonMonthYear();
  const cashflow = result.cashflow || [];
  const years = cashflowYears(cashflow);
  if (!years.length) {
    section.hidden = true;
    return;
  }
  if (!horizonMonthYear || !years.includes(horizonMonthYear)) {
    horizonMonthYear = defaultHorizonMonthYear(cashflow, result.purchase_date);
  }
  yearSelect.innerHTML = years.map((year) => `<option value="${year}">${year}</option>`).join("");
  yearSelect.value = horizonMonthYear;
  const point = horizonMonthPointForYear(cashflow, horizonMonthYear);
  if (!point) {
    section.hidden = true;
    return;
  }
  buyList.innerHTML = horizonMonthRows(point, HORIZON_MONTH_BUY, real);
  rentList.innerHTML = horizonMonthRows(point, HORIZON_MONTH_RENT, real);
  const note = document.getElementById("horizon-month-ubrig-note");
  const buyLeft = flowAmount(point, "buy_left", real);
  const rentLeft = flowAmount(point, "rent_left", real);
  if (note) note.hidden = buyLeft >= -1 && rentLeft >= -1;
  section.hidden = !buyList.innerHTML && !rentList.innerHTML;
}

function drawFlows(points, real, markers) {
  const wealthMarks = (markers || []).filter((marker) => marker.chart === "wealth");
  paintStack(
    document.getElementById("rent-flow"),
    document.getElementById("legend-rent-flow"),
    points,
    RENT_FLOW,
    "rent_draw",
    real,
    wealthMarks,
    "rent-flow",
  );
  paintStack(
    document.getElementById("buy-flow"),
    document.getElementById("legend-buy-flow"),
    points,
    BUY_FLOW,
    "buy_draw",
    real,
    wealthMarks,
    "buy-flow",
  );
}

function flowAmount(point, key, real) {
  const amount = Number(point[key]) || 0;
  return real ? amount / (point.inflation || 1) : amount;
}

function flowUbrigChartValue(point, leftKey, real, _chartKey) {
  return flowAmount(point, leftKey, real);
}

function flowStackAxisMax(totals, draws, leftValues) {
  let max = Math.max(1, ...totals, ...draws);
  for (let index = 0; index < leftValues.length; index += 1) {
    const left = leftValues[index];
    if (left < -1) continue;
    max = Math.max(max, (totals[index] || 0) + Math.max(0, left));
  }
  return max;
}

function segmentTouchesMarker(series, index, markers, chartKeys) {
  if (!markers?.length || index >= series.length - 1) return false;
  const start = series[index].date;
  const end = series[index + 1].date;
  return markers.some((marker) => {
    if (!chartKeys.includes(marker.chart)) return false;
    const when = marker.date;
    return when > start && when <= end;
  });
}

function loanBalanceSegmentSteps(values, index) {
  const left = Number(values[index]) || 0;
  const right = Number(values[index + 1]) || 0;
  return (left <= 1 && right > 1) || (left > 1 && right <= 1);
}

function etfSegmentSteps(values, index) {
  const left = Number(values[index]) || 0;
  const right = Number(values[index + 1]) || 0;
  return (left > 1 && right < -1) || (left < -1 && right > 1);
}

function chartMarkerKeys(chartPrefix, klass) {
  if (chartPrefix === "loan" || klass === "loan") return ["loan", "both"];
  return ["wealth", "both"];
}

/** Slopes between years when the series continues; vertical steps at jumps. */
function chartStepLineD(x, values, y, options = {}) {
  const continuousSegment = options.continuousSegment ?? (() => false);
  if (!values.length) return "";
  let d = `M${x(0).toFixed(1)},${y(values[0]).toFixed(1)}`;
  for (let i = 0; i < values.length - 1; i += 1) {
    const x1 = x(i + 1).toFixed(1);
    const y1 = y(values[i + 1]).toFixed(1);
    if (continuousSegment(i)) d += ` L${x1},${y1}`;
    else d += ` H${x1} V${y1}`;
  }
  return d;
}

function chartStepAreaD(x, values, y, options = {}) {
  const continuousSegment = options.continuousSegment ?? (() => false);
  if (!values.length) return "";
  const base = y(0).toFixed(1);
  let d = `M${x(0).toFixed(1)},${y(values[0]).toFixed(1)}`;
  for (let i = 0; i < values.length - 1; i += 1) {
    const x1 = x(i + 1).toFixed(1);
    const y1 = y(values[i + 1]).toFixed(1);
    if (continuousSegment(i)) d += ` L${x1},${y1}`;
    else d += ` H${x1} V${y1}`;
  }
  d += ` H${x(values.length - 1).toFixed(1)} V${base} H${x(0).toFixed(1)} Z`;
  return d;
}

function chartStackLayerStepD(x, y, rows, layerIndex) {
  const n = rows.length;
  if (n < 2) return "";
  const topAt = (idx) => rows[idx].slice(0, layerIndex + 1).reduce((total, value) => total + value, 0);
  const botAt = (idx) => rows[idx].slice(0, layerIndex).reduce((total, value) => total + value, 0);
  const parts = [];
  for (let i = 0; i < n - 1; i += 1) {
    const x0 = x(i).toFixed(1);
    const x1 = x(i + 1).toFixed(1);
    const t0 = y(topAt(i)).toFixed(1);
    const b0 = y(botAt(i)).toFixed(1);
    parts.push(`M${x0},${b0} H${x1} V${t0} H${x0} Z`);
  }
  return parts.join("");
}

function flowLayerVisible(layerKey, points, real) {
  if (FLOW_LEFT_KEYS.has(layerKey)) return true;
  return points.some((point) => flowAmount(point, layerKey, real) > 1);
}

function stackLayerValue(layerKey, value) {
  if (FLOW_LEFT_KEYS.has(layerKey)) return value;
  return Math.max(0, value);
}

function ubrigAreaMarkup(points, leftKey, real, x, y, totals, chartKey) {
  const fills = [];
  const warn = [];
  for (let index = 0; index < points.length - 1; index += 1) {
    const value = flowUbrigChartValue(points[index], leftKey, real, chartKey);
    const total = totals[index] || 0;
    if (value < -1) continue;
    const top = total + Math.max(0, value);
    const x0 = x(index).toFixed(1);
    const x1 = x(index + 1).toFixed(1);
    fills.push(
      `<path class="flow-ubrig-fill" d="M${x0},${y(total).toFixed(1)} H${x1} V${y(top).toFixed(1)} H${x0} Z" />`,
    );
  }
  for (let index = 0; index < points.length; index += 1) {
    const value = flowUbrigChartValue(points[index], leftKey, real, chartKey);
    if (value >= -1) continue;
    const px = x(index).toFixed(1);
    const py = y(value).toFixed(1);
    warn.push(`M${px},${y(0).toFixed(1)} L${px},${py}`);
  }
  return [...fills, ...warn.map((path) => `<path class="flow-ubrig-warn-line" d="${path}" />`)].join("");
}

function paintStack(svg, legend, points, layers, drawKey, real, markers, chartKey) {
  if (!svg) return;
  const shown = layers.filter((layer) => flowLayerVisible(layer[0], points, real));
  const draw = points.some((point) => flowAmount(point, drawKey, real) > 150);
  if (legend) {
    const items = shown.map(([, label, color]) => `<span class="swatch flow-swatch" style="background:${color}"></span>${label}`);
    if (draw) items.push(`<span class="swatch flow-swatch" style="background:#9f1239"></span>ETF-Entnahme`);
    legend.innerHTML = items.join("");
  }
  const width = 800;
  const padX = 92;
  const padBottom = 26;
  const plotHeight = 200;
  const x = (index) => padX + (index / Math.max(1, points.length - 1)) * (width - padX * 2);
  const stackLayers = shown.filter((layer) => !FLOW_LEFT_KEYS.has(layer[0]));
  const rows = points.map((point) =>
    stackLayers.map((layer) => Math.max(0, flowAmount(point, layer[0], real))),
  );
  const totals = rows.map((row) => row.reduce((sum, value) => sum + value, 0));
  const draws = points.map((point) => Math.max(0, flowAmount(point, drawKey, real)));
  const leftLayerKey = shown.find((layer) => FLOW_LEFT_KEYS.has(layer[0]))?.[0];
  const leftValues = leftLayerKey
    ? points.map((point) => flowUbrigChartValue(point, leftLayerKey, real, chartKey))
    : [];
  const scale = valueScale(
    leftValues.length ? Math.min(0, ...leftValues) : 0,
    flowStackAxisMax(totals, draws, leftValues),
  );
  if (!points.length) {
    svg.innerHTML = "";
    return;
  }
  const flowMarkers = (markers || []).map((marker) => ({ ...marker, chart: chartKey }));
  const placed = layoutMarkers(svg, points, flowMarkers, chartKey, x, width);
  const rowHeight = 18;
  const markerRows = placed.reduce((highest, marker) => Math.max(highest, marker.row), -1) + 1;
  const band = markerRows === 0 ? 8 : markerRows * rowHeight + 22;
  const height = band + plotHeight + padBottom;
  const y = (value) => band + plotHeight - ((value - scale.axisMin) / (scale.axisMax - scale.axisMin)) * plotHeight;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const areas = stackLayers
    .map(
      (layer, layerIndex) =>
        `<path fill="${layer[2]}" fill-opacity="0.88" d="${chartStackLayerStepD(x, y, rows, layerIndex)}" />`,
    )
    .join("");
  const withdrawal = draw ? `<path class="flow-line" d="${chartStepLineD(x, draws, y)}" />` : "";
  const ticks = yearTicks(points, x).map((tick) => {
    const anchor = tick.x < padX + 16 ? "start" : tick.x > width - padX - 16 ? "end" : "middle";
    return `<line class="tick-mark" x1="${tick.x.toFixed(1)}" y1="${y(0)}" x2="${tick.x.toFixed(1)}" y2="${y(0) + 5}" /><text class="tick" text-anchor="${anchor}" x="${tick.x.toFixed(1)}" y="${height - 8}">${tick.year}</text>`;
  }).join("");
  const levels = scale.ticks.map((value) => {
    const lineY = y(value).toFixed(1);
    const grid = value === 0 ? "" : `<line class="grid" x1="${padX}" y1="${lineY}" x2="${width - padX}" y2="${lineY}" />`;
    return `${grid}<text class="tick" text-anchor="end" x="${padX - 8}" y="${Number(lineY) + 4}">${axisAmount(value)}</text>`;
  }).join("");
  const series = shown.map((layer, layerIndex) => ({
    label: layer[1],
    color: layer[2],
    key: layer[0],
    values: points.map((point) => flowAmount(point, layer[0], real)),
  }));
  if (draw) series.push({ label: "ETF-Entnahme", color: "#9f1239", values: draws });
  const marks = placed.map((marker) => {
    const index = points.findIndex((point) => point.date >= marker.date);
    const useIndex = index < 0 ? points.length - 1 : index;
    const stackTop = totals[useIndex] || 0;
    const lineX = marker.x;
    const labelX = marker.left + marker.w / 2;
    const labelY = 14 + marker.row * rowHeight;
    const stemTop = labelY + 4;
    const elbowY = stemTop + 8;
    const stem = Math.abs(labelX - lineX) < 1.5
      ? `M${labelX.toFixed(1)},${stemTop} L${lineX.toFixed(1)},${y(stackTop)}`
      : `M${labelX.toFixed(1)},${stemTop} L${labelX.toFixed(1)},${elbowY} L${lineX.toFixed(1)},${y(stackTop)}`;
    return `<line class="marker" style="stroke:${marker.color}" x1="${lineX.toFixed(1)}" y1="${y(stackTop)}" x2="${lineX.toFixed(1)}" y2="${y(0)}" />
      <path class="marker-stem" style="stroke:${marker.color}" d="${stem}" />
      <circle class="marker-dot" style="fill:${marker.color}" cx="${lineX.toFixed(1)}" cy="${y(stackTop)}" r="3.2" />
      <text class="marker-label" style="fill:${marker.color}" x="${labelX.toFixed(1)}" y="${labelY}" text-anchor="middle">${marker.label}</text>`;
  }).join("");
  const ubrigOverlay = leftLayerKey
    ? ubrigAreaMarkup(points, leftLayerKey, real, x, y, totals, chartKey)
    : "";
  svg.innerHTML = `<line class="axis" x1="${padX}" y1="${y(0)}" x2="${width - padX}" y2="${y(0)}" />${levels}${areas}${withdrawal}${ubrigOverlay}${ticks}${marks}
    <line class="hover-guide" visibility="hidden" />
    <rect class="hover-catch" x="${padX}" y="${band}" width="${width - padX * 2}" height="${plotHeight}" fill="transparent" />`;
  bindPlotHover(svg, { points, series, x, band, plotHeight });
}

const PLOT_TAP_MOVE_PX = 12;

function plotUsesTap() {
  return window.matchMedia("(hover: none), (pointer: coarse)").matches;
}

let plotOutsideDismissBound = false;

function bindPlotOutsideDismiss() {
  if (plotOutsideDismissBound) return;
  plotOutsideDismissBound = true;
  document.addEventListener(
    "pointerdown",
    (event) => {
      if (!plotUsesTap()) return;
      document.querySelectorAll(".plot").forEach((plot) => {
        const svg = plot.querySelector("svg[data-hover-bound]");
        if (!svg?._plotPinned) return;
        if (plot.contains(event.target)) return;
        hidePlotTip(svg);
      });
    },
    true,
  );
}

function plotIndexAt(svg, event) {
  const state = svg._plot;
  const rect = svg.getBoundingClientRect();
  const view = svg.viewBox.baseVal;
  const viewX = ((event.clientX - rect.left) / rect.width) * view.width;
  let index = 0;
  let best = Infinity;
  for (let i = 0; i < state.points.length; i += 1) {
    const distance = Math.abs(state.x(i) - viewX);
    if (distance < best) {
      best = distance;
      index = i;
    }
  }
  return index;
}

function dismissOtherPlotTips(activeSvg) {
  document.querySelectorAll(".plot svg[data-hover-bound]").forEach((svg) => {
    if (svg === activeSvg) return;
    hidePlotTip(svg);
  });
}

function tipColor(hex) {
  const value = Number.parseInt(hex.slice(1), 16);
  const red = (value >> 16) & 255;
  const green = (value >> 8) & 255;
  const blue = value & 255;
  const luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255;
  return luminance > 0.55 ? "#475569" : hex;
}

function plotTip(svg) {
  let tip = svg.parentElement.querySelector(".plot-tip");
  if (!tip) {
    tip = document.createElement("div");
    tip.className = "plot-tip";
    tip.hidden = true;
    svg.after(tip);
  }
  return tip;
}

function showPlotTip(svg, event, { pin = false } = {}) {
  const state = svg._plot;
  if (!state || !state.points.length) return;
  const index = plotIndexAt(svg, event);
  const guide = svg.querySelector(".hover-guide");
  const xPos = state.x(index).toFixed(1);
  guide.setAttribute("x1", xPos);
  guide.setAttribute("x2", xPos);
  guide.setAttribute("y1", state.band);
  guide.setAttribute("y2", state.band + state.plotHeight);
  guide.setAttribute("visibility", "visible");
  const year = state.points[index].date.slice(0, 4);
  const leftVal = state.series.find((item) => item.label === "Übrig")?.values[index] ?? 0;
  const rows = state.series
    .filter((item) => {
      const value = item.values[index];
      if (Math.abs(value) <= 0.5) return false;
      const isEtf = item.label === "ETF" || item.label === "ETF-Entnahme";
      if (isEtf && leftVal < -1) return false;
      return true;
    })
    .map((item) => {
      const value = item.values[index];
      const color =
        item.label === "Übrig" && value < -1
          ? FLOW_WARN_COLOR
          : item.label === "Übrig"
            ? UBRIG_GREY
            : tipColor(item.color);
      return `<div class="tip-row" style="color:${color}">${item.label} ${euro.format(value)}</div>`;
    })
    .join("");
  const tip = plotTip(svg);
  tip.innerHTML = `<div class="tip-x">${year}</div>${rows}`;
  tip.hidden = false;
  if (pin) {
    dismissOtherPlotTips(svg);
    svg._plotPinned = true;
  }
  positionPlotTip(svg, tip, index, event);
}

function positionPlotTip(svg, tip, index, event) {
  const state = svg._plot;
  const rect = svg.getBoundingClientRect();
  const view = svg.viewBox.baseVal;
  const margin = 10;
  if (plotUsesTap() && svg._plotPinned) {
    const pointX = rect.left + (state.x(index) / view.width) * rect.width;
    tip.style.position = "fixed";
    tip.style.maxWidth = `${Math.min(288, window.innerWidth - margin * 2)}px`;
    let left = pointX + 14;
    tip.hidden = false;
    const width = tip.offsetWidth;
    if (left + width > window.innerWidth - margin) {
      left = Math.max(margin, pointX - width - 14);
    }
    left = Math.max(margin, Math.min(left, window.innerWidth - margin - width));
    let top = event.clientY - tip.offsetHeight - 10;
    top = Math.max(margin, Math.min(top, window.innerHeight - margin - tip.offsetHeight));
    tip.style.left = `${left}px`;
    tip.style.top = `${top}px`;
    return;
  }
  tip.style.position = "absolute";
  tip.style.maxWidth = "";
  const plot = svg.parentElement.getBoundingClientRect();
  const pointX = rect.left - plot.left + (state.x(index) / view.width) * rect.width;
  let left = pointX + 14;
  if (left + tip.offsetWidth > plot.width - 4) left = Math.max(4, pointX - tip.offsetWidth - 14);
  const top = Math.min(
    Math.max(4, event.clientY - plot.top - tip.offsetHeight - 10),
    plot.height - tip.offsetHeight - 4,
  );
  tip.style.left = `${left}px`;
  tip.style.top = `${top}px`;
}

function hidePlotTip(svg) {
  svg._plotPinned = false;
  svg.querySelector(".hover-guide")?.setAttribute("visibility", "hidden");
  const tip = svg.parentElement?.querySelector(".plot-tip");
  if (!tip) return;
  tip.hidden = true;
  tip.style.position = "";
  tip.style.left = "";
  tip.style.top = "";
  tip.style.maxWidth = "";
}

function bindPlotHover(svg, state) {
  svg._plot = state;
  hidePlotTip(svg);
  bindPlotOutsideDismiss();
  if (svg.dataset.hoverBound) return;
  svg.dataset.hoverBound = "1";
  const onCatch = (target) => target?.classList?.contains("hover-catch") || target?.closest?.(".hover-catch");
  if (!plotUsesTap()) {
    svg.addEventListener("pointermove", (event) => showPlotTip(svg, event));
    svg.addEventListener("pointerleave", () => hidePlotTip(svg));
    return;
  }
  let activePointer = null;
  svg.addEventListener(
    "pointerdown",
    (event) => {
      if (!onCatch(event.target)) return;
      activePointer = { id: event.pointerId, x: event.clientX, y: event.clientY };
    },
    { passive: true },
  );
  svg.addEventListener(
    "pointerup",
    (event) => {
      if (!activePointer || event.pointerId !== activePointer.id) return;
      const dx = event.clientX - activePointer.x;
      const dy = event.clientY - activePointer.y;
      activePointer = null;
      if (Math.hypot(dx, dy) > PLOT_TAP_MOVE_PX) return;
      if (!onCatch(event.target)) return;
      showPlotTip(svg, event, { pin: true });
    },
    { passive: true },
  );
}

function xAt(series, date, xOf) {
  // Samples are year-end. January would otherwise fall on the previous December.
  if (!series.length || date < series[0].date || date > series.at(-1).date) return null;
  let index = 0;
  while (index < series.length - 1 && series[index].date < date) index += 1;
  return xOf(index);
}

function measureLabels(svg, labels) {
  svg.innerHTML = labels.map((label, index) => `<text class="marker-label" data-probe="${index}" x="0" y="20">${label}</text>`).join("");
  return labels.map((_, index) => svg.querySelector(`[data-probe="${index}"]`).getBBox().width + 8);
}

const MARKER_COLORS = ["#0f766e", "#c2410c", "#6d28d9", "#0369a1", "#b45309", "#be185d"];

function layoutMarkers(svg, series, markers, chart, xOf, width) {
  const gap = 8;
  const items = (markers || [])
    .filter((marker) => marker.chart === chart)
    .map((marker) => ({
      ...marker,
      x: xAt(series, marker.date, xOf),
    }))
    .filter((marker) => marker.x != null)
    .sort((a, b) => a.x - b.x);
  const widths = items.length ? measureLabels(svg, items.map((marker) => marker.label)) : [];
  items.forEach((marker, index) => {
    marker.w = widths[index];
    marker.color = MARKER_COLORS[index % MARKER_COLORS.length];
  });

  const occupied = [];
  const hits = (left, right, row) => occupied.some((item) => item.row === row && left < item.right + gap && right > item.left);
  const placed = [];
  for (const marker of items) {
    const left = Math.min(Math.max(4, marker.x - marker.w / 2), width - 4 - marker.w);
    let row = 0;
    while (
      hits(left, left + marker.w, row) ||
      placed.some(
        (other) =>
          other.row === row && Math.abs(other.x - marker.x) < (other.w + marker.w) / 2 + gap,
      )
    ) {
      row += 1;
    }
    occupied.push({ row, left, right: left + marker.w });
    placed.push({ ...marker, left, row });
  }
  return placed;
}

function axisAmount(value) {
  const abs = Math.abs(value);
  const format = (number, digits) => new Intl.NumberFormat("de-DE", { maximumFractionDigits: digits }).format(number);
  if (abs >= 1_000_000) return `${format(value / 1_000_000, Number.isInteger(value / 1_000_000) ? 0 : 1)} Mio. €`;
  if (abs >= 1_000) return `${format(value / 1_000, Number.isInteger(value / 1_000) ? 0 : 1)} Tsd. €`;
  return euro.format(value);
}

function valueScale(min, max) {
  const span = Math.max(max - min, 1);
  const rough = span / 4;
  const power = 10 ** Math.floor(Math.log10(rough));
  const fraction = rough / power;
  const factor = fraction >= 7.5 ? 10 : fraction >= 3.5 ? 5 : fraction >= 1.5 ? 2 : 1;
  const step = factor * power;
  const axisMin = Math.floor(min / step) * step;
  const axisMax = Math.max(step, Math.ceil(max / step) * step);
  const ticks = [];
  for (let value = axisMin; value <= axisMax + step * 0.001; value += step) ticks.push(Math.round(value));
  return { axisMin, axisMax, ticks };
}

function paintChart(svg, series, specs, values, plotHeight, prefix, markers) {
  const width = 800;
  const padX = 92;
  const padBottom = 26;
  const rowHeight = 18;
  const min = Math.min(0, ...values);
  const max = Math.max(1, ...values);
  const scale = valueScale(min, max);
  const x = (index) => padX + (index / Math.max(1, series.length - 1)) * (width - padX * 2);
  const placed = layoutMarkers(svg, series, markers, prefix, x, width);
  const rows = placed.reduce((highest, marker) => Math.max(highest, marker.row), -1) + 1;
  const band = rows === 0 ? 8 : rows * rowHeight + 22;
  const height = band + plotHeight + padBottom;
  const y = (value) => band + plotHeight - ((value - scale.axisMin) / (scale.axisMax - scale.axisMin)) * plotHeight;
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const colors = { buy: BUY_COLOR, rent: RENT_COLOR, loan: BUY_COLOR, etf: BUY_ETF_COLOR };
  const lineLabels = { buy: "Kaufen", rent: "Mieten", loan: "Restschuld", etf: "ETF im Kauf" };
  const paths = specs.map(([key, klass]) => {
    const lineValues = series.map((point) => point[key]);
    const markerKeys = chartMarkerKeys(prefix, klass);
    const continuousSegment = (index) => {
      if (segmentTouchesMarker(series, index, markers, markerKeys)) return false;
      if (klass === "loan" && loanBalanceSegmentSteps(lineValues, index)) return false;
      if (klass === "etf" && etfSegmentSteps(lineValues, index)) return false;
      return true;
    };
    const line = chartStepLineD(x, lineValues, y, { continuousSegment });
    const color = colors[klass] || RENT_COLOR;
    const fill =
      klass === "etf"
        ? ""
        : `<path fill="${color}" fill-opacity="0.14" d="${chartStepAreaD(x, lineValues, y, { continuousSegment })}" />`;
    return `${fill}<path class="${klass}-line" fill="none" d="${line}" />`;
  }).join("");
  const marks = placed.map((marker) => {
    const labelX = marker.left + marker.w / 2;
    const labelY = 14 + marker.row * rowHeight;
    const lineX = marker.x;
    const stemTop = labelY + 4;
    const elbowY = stemTop + 8;
    const stem = Math.abs(labelX - lineX) < 1.5
      ? `M${labelX.toFixed(1)},${stemTop} L${lineX.toFixed(1)},${band}`
      : `M${labelX.toFixed(1)},${stemTop} L${labelX.toFixed(1)},${elbowY} L${lineX.toFixed(1)},${band}`;
    return `<line class="marker" style="stroke:${marker.color}" x1="${lineX.toFixed(1)}" y1="${band}" x2="${lineX.toFixed(1)}" y2="${y(0).toFixed(1)}" />
      <path class="marker-stem" style="stroke:${marker.color}" d="${stem}" />
      <circle class="marker-dot" style="fill:${marker.color}" cx="${lineX.toFixed(1)}" cy="${band}" r="3.2" />
      <text class="marker-label" style="fill:${marker.color}" x="${labelX.toFixed(1)}" y="${labelY}" text-anchor="middle">${marker.label}</text>`;
  }).join("");
  const ticks = yearTicks(series, x).map((tick) => {
    const anchor = tick.x < padX + 16 ? "start" : tick.x > width - padX - 16 ? "end" : "middle";
    return `<line class="tick-mark" x1="${tick.x.toFixed(1)}" y1="${y(0)}" x2="${tick.x.toFixed(1)}" y2="${y(0) + 5}" /><text class="tick" text-anchor="${anchor}" x="${tick.x.toFixed(1)}" y="${height - 8}">${tick.year}</text>`;
  }).join("");
  const levels = scale.ticks.map((value) => {
    const lineY = y(value).toFixed(1);
    const grid = value === 0 ? "" : `<line class="grid" x1="${padX}" y1="${lineY}" x2="${width - padX}" y2="${lineY}" />`;
    return `${grid}<text class="tick" text-anchor="end" x="${padX - 8}" y="${Number(lineY) + 4}">${axisAmount(value)}</text>`;
  }).join("");
  svg.innerHTML = `<line class="axis" x1="${padX}" y1="${y(0)}" x2="${width - padX}" y2="${y(0)}" />
    ${levels}
    ${paths}
    ${ticks}
    ${marks}
    <line class="hover-guide" visibility="hidden" />
    <rect class="hover-catch" x="${padX}" y="${band}" width="${width - padX * 2}" height="${plotHeight}" fill="transparent" />`;
  bindPlotHover(svg, {
    points: series,
    series: specs.map(([key, klass]) => ({
      label: lineLabels[klass],
      color: colors[klass],
      values: series.map((point) => point[key]),
    })),
    x,
    band,
    plotHeight,
  });
}

function yearTicks(series, xOf) {
  if (!series.length) return [];
  const startYear = Number(series[0].date.slice(0, 4));
  const endYear = Number(series.at(-1).date.slice(0, 4));
  const span = endYear - startYear;
  const step = span > 55 ? 10 : span > 30 ? 5 : span > 14 ? 2 : 1;
  const ticks = [];
  const first = Math.ceil(startYear / step) * step;
  for (let year = first; year <= endYear; year += step) {
    const pos = xAt(series, `${year}-01-01`, xOf);
    if (pos != null) ticks.push({ year, x: pos });
  }
  const bounds = [
    { year: startYear, x: xOf(0) },
    { year: endYear, x: xOf(series.length - 1) },
  ];
  for (const bound of bounds) {
    if (!ticks.some((tick) => Math.abs(tick.x - bound.x) < YEAR_TICK_MIN_GAP)) ticks.push(bound);
  }
  ticks.sort((a, b) => a.x - b.x);
  const kept = [];
  for (const tick of ticks) {
    if (!kept.length || tick.x - kept.at(-1).x >= YEAR_TICK_MIN_GAP) {
      kept.push(tick);
      continue;
    }
    if (tick.year === endYear) kept[kept.length - 1] = tick;
  }
  return kept;
}