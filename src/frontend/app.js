const euro = new Intl.NumberFormat("de-DE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

let scenario = null;
let latest = null;
let timer = null;
let requestId = 0;
let bundeslaender = ["Bayern"];
let scenarioSnapshot = null;
let touchedSnapshot = null;
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

const SLIDER_GROUP_ORDER = ["Zeit", "Vermögen", "Wohnen", "Zins", "Regeln", "Pflege"];

const BELIEF_SLIDER_GROUP = {
  rent_growth: "Wohnen",
  owner_cost_growth: "Wohnen",
  appreciation: "Wohnen",
  inflation: "Wohnen",
  etf_return: "Vermögen",
  ter: "Vermögen",
  basiszins: "Regeln",
  tilgung: "Zins",
  zinsbindung_years: "Zins",
  sollzins: "Zins",
  anschlusszins: "Zins",
};

function emptySliderBuckets() {
  return Object.fromEntries(SLIDER_GROUP_ORDER.map((name) => [name, []]));
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

function ownerCostsRateFromEuros() {
  const price = scenario.dwelling.purchase_price;
  if (!price) return 0;
  return (scenario.dwelling.owner_costs * 12) / price;
}

function syncOwnerCostsFromRate(rate) {
  scenario.dwelling.owner_costs_rate = rate;
  scenario.dwelling.owner_costs = (scenario.dwelling.purchase_price * rate) / 12;
}

function syncOwnerRateFromEuros() {
  const rate = ownerCostsRateFromEuros();
  scenario.dwelling.owner_costs_rate = rate;
  return rate;
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
    const open = !tip.hidden;
    document.querySelectorAll(".info-tip").forEach((node) => {
      node.hidden = true;
    });
    tip.hidden = open;
  });
  const wrap = document.createElement("span");
  wrap.className = "info-wrap";
  wrap.append(button, tip);
  return wrap;
}

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
    ["Eigentümerkosten im Monat", "Eigentümerkosten"],
    ["Anteil des Kaufpreises", "Ein niedrigerer Anteil"],
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
  scenario.adults.forEach((adult) => {
    if (!Number.isFinite(Number(adult.gross_salary))) adult.gross_salary = 0;
    if (!Number.isFinite(Number(adult.depot))) adult.depot = 0;
    if (!Number.isFinite(Number(adult.sparrate))) adult.sparrate = 0;
    if (!Number.isFinite(Number(adult.kaltmiete))) adult.kaltmiete = 0;
    if (!Number.isFinite(Number(adult.retire_age))) adult.retire_age = 67;
    if (!Number.isFinite(Number(adult.care_age))) adult.care_age = 75;
    if (!Number.isFinite(Number(adult.salary_growth))) adult.salary_growth = 0.02;
    if (adult.church_tax == null) adult.church_tax = false;
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
  range.addEventListener("input", () => {
    const next = coalesceNumber(range.value, start);
    out.textContent = formatValue(next, unit, step);
    paintRange(range);
    onInput(next);
    schedule();
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

function mountBeliefs() {
  const host = document.getElementById("beliefs");
  host.innerHTML = "";
  normalizeSliderScenario();
  if (scenario.beliefs?.church_tax) {
    scenario.adults.forEach((adult) => {
      if (!adult.church_tax) adult.church_tax = true;
    });
    scenario.beliefs.church_tax = false;
  }
  const buckets = emptySliderBuckets();
  const d = scenario.dwelling;
  const ownerRateShown = syncOwnerRateFromEuros();
  buckets.Wohnen.push(
    slider("purchase_price", "Kaufpreis", 50_000, 2_000_000, 5_000, d.purchase_price, "€", (value) => {
      d.purchase_price = value;
      const rate = syncOwnerRateFromEuros();
      setControlDisplay("Eigentümerkosten, Anteil des Kaufpreises im Jahr", rate, "%", 0.0005);
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
    slider("owner_costs", "Eigentümerkosten im Monat", 0, 2_000, 10, d.owner_costs, "€", (value) => {
      d.owner_costs = value;
      const rate = syncOwnerRateFromEuros();
      setControlDisplay("Eigentümerkosten, Anteil des Kaufpreises im Jahr", rate, "%", 0.0005);
    }, assumptionLine("Eigentümerkosten")),
    slider(
      "owner_costs_rate",
      "Eigentümerkosten, Anteil des Kaufpreises im Jahr",
      0,
      0.03,
      0.0005,
      ownerRateShown,
      "%",
      (value) => {
        syncOwnerCostsFromRate(value);
        setControlDisplay("Eigentümerkosten im Monat", scenario.dwelling.owner_costs, "€", 10);
      },
      assumptionLine("Ein niedrigerer Anteil"),
    ),
  );
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
    buckets.Zeit.push(
      slider(`retire-${adult.id}`, `${name}: Rentenalter`, 55, 75, 1, adult.retire_age, "years", (value) => {
        adult.retire_age = Math.round(value);
      }),
      slider(`care-${adult.id}`, `${name}: Pflegealter`, 60, 95, 1, adult.care_age, "years", (value) => {
        adult.care_age = Math.round(value);
      }),
    );
  });
  const horizonAge = scenario.horizon?.age ?? 100;
  buckets.Zeit.push(
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
      slider(`gross-${adult.id}`, `${name}: Brutto im Jahr`, 0, 300_000, 1_000, adult.gross_salary, "€", (value) => {
        adult.gross_salary = value;
      }, assumptionLine("Jede Person spart")),
      slider(`growth-${adult.id}`, `${name}: Gehaltswachstum`, 0, 0.1, 0.001, adult.salary_growth, "%", (value) => {
        adult.salary_growth = value;
      }),
      slider(`depot-${adult.id}`, `${name}: Depot`, 0, 500_000, 1_000, adult.depot, "€", (value) => {
        adult.depot = value;
      }, assumptionLine("Die ETF-Depots")),
      slider(`spar-${adult.id}`, `${name}: Sparrate im Monat`, 0, 10_000, 50, adult.sparrate, "€", (value) => {
        adult.sparrate = value;
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
    buckets.Vermögen.push(
      slider(`pension-${adult.id}`, pensionLabel, 0, 6000, 10, pension, "€", (value) => {
        touched.pensions[adult.id] = true;
        adult.pension_gross_today = value;
      }, assumptionLine("Die gesetzliche Rente")),
    );
  });
  buckets.Vermögen.push(
    slider("equity_cash", "Bargeld außerhalb des Depots", 0, 500_000, 1_000, scenario.equity_cash, "€", (value) => {
      scenario.equity_cash = value;
    }, assumptionLine("Zusätzliches Eigenkapital")),
  );
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
    const group = BELIEF_SLIDER_GROUP[name] || "Regeln";
    buckets[group].push(slider(name, label, min, max, step, shown, unit, (value) => setBelief(name, value)));
  }
  mountEtfChoice(buckets);
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
    } else if (name === "inflation") {
      buckets.Wohnen.push(
        slider(name, label, min, max, step, beliefValue(name), unit, (value) => setBelief(name, value), assumptionLine("Die Inflation")),
      );
    }
  }
  const equity = document.createElement("label");
  equity.className = "switch belief-switch";
  equity.innerHTML = `<input type="checkbox" ${scenario.dwelling.min_equity ? "checked" : ""}><span class="track"></span><span class="switch-text">Erst bei 15 % inklusive Nebenkosten kaufen</span>`;
  equity.querySelector("input").addEventListener("change", (event) => {
    scenario.dwelling.min_equity = event.target.checked;
    schedule();
  });
  buckets.Wohnen.push(equity);
  buckets.Pflege.push(
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
  const household = document.createElement("label");
  household.className = "switch belief-switch";
  household.innerHTML = `<input type="checkbox" ${scenario.beliefs.household_rate !== false ? "checked" : ""}><span class="track"></span><span class="switch-text">Zins nach der Haushaltslage</span>`;
  household.querySelector("input").addEventListener("change", (event) => {
    scenario.beliefs.household_rate = event.target.checked;
    if (!touched.sollzins) scenario.beliefs.sollzins = null;
    schedule();
  });
  buckets.Zins.push(household);
  scenario.adults.forEach((adult, index) => {
    const name = adult.label || (index === 0 ? "Du" : "Zweite Person");
    const church = document.createElement("label");
    church.className = "switch belief-switch";
    church.innerHTML = `<input type="checkbox" ${adult.church_tax ? "checked" : ""}><span class="track"></span><span class="switch-text">Kirchensteuer: ${name}</span>`;
    church.querySelector("input").addEventListener("change", (event) => {
      adult.church_tax = event.target.checked;
      schedule();
    });
    buckets.Regeln.push(church);
  });
  buckets.Regeln.push(
    slider("basiszins", "Basiszins Vorabpauschale", 0, 0.06, 0.0001, beliefValue("basiszins"), "%", (value) => setBelief("basiszins", value)),
  );
  mountSliderGroups(host, buckets);
}

function schedule() {
  clearTimeout(timer);
  timer = setTimeout(run, 200);
}

async function run() {
  const id = ++requestId;
  const body = structuredClone(scenario);
  if (!touched.sollzins) body.beliefs.sollzins = null;
  if (!touched.anschlusszins) body.beliefs.anschlusszins = null;
  for (const adult of body.adults) {
    if (!touched.pensions[adult.id]) adult.pension_gross_today = null;
  }
  const response = await fetch("/api/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
  scenarioSnapshot = structuredClone(scenario);
  touchedSnapshot = {
    sollzins: touched.sollzins,
    anschlusszins: touched.anschlusszins,
    pensions: { ...touched.pensions },
  };
  renderResult(latest);
  syncBeliefDisplays();
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
  if (scenario.dwelling.move_in_cost_2026 == null) scenario.dwelling.move_in_cost_2026 = 0;
  if (!scenario.beliefs) scenario.beliefs = {};
  touched.sollzins = scenario.beliefs.sollzins != null;
  touched.anschlusszins = scenario.beliefs.anschlusszins != null;
  touched.pensions = {};
  document.getElementById("banner").hidden = !demo;
  document.getElementById("gate").hidden = true;
  document.getElementById("chat").hidden = true;
  document.getElementById("results").hidden = false;
  await loadBundeslaender();
  mountBeliefs();
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
  }
  window.scenarioStore.saveOpenRow(body);
  document.getElementById("banner").hidden = true;
  window.showGate();
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
      <article class="hero buy"><span>Kaufen</span><strong>${summaryAmount(buy)}</strong></article>
      <p class="hero-gap delta ${gapTone(buy, rent)}">${gapText(buy, rent)}</p>
      <article class="hero rent"><span>Mieten</span><strong>${summaryAmount(rent)}</strong></article>
    </div>
  `;
  const gapEl = document.querySelector("#figures .hero-gap");
  if (gapEl && gapInfo) gapEl.append(infoButton(gapInfo));
  const gaps = document.getElementById("life-gaps");
  if (careBuy != null && careRent != null) {
    gaps.innerHTML = `
      <p class="care-label">Bei Pflegebeginn</p>
      <div class="hero-grid care-compact">
        <article class="hero buy"><span>Kaufen</span><strong>${summaryAmount(careBuy)}</strong></article>
        <p class="hero-gap delta ${gapTone(careBuy, careRent)}">${gapText(careBuy, careRent)}</p>
        <article class="hero rent"><span>Mieten</span><strong>${summaryAmount(careRent)}</strong></article>
      </div>`;
  } else {
    gaps.innerHTML = "";
  }
  const life = document.getElementById("life-sentence");
  if (life) life.replaceChildren();
  const factorInterest = document.getElementById("factor-interest");
  if (factorInterest) factorInterest.replaceChildren();
  syncPurchasePriceInfo();
  document.getElementById("warnings").innerHTML = result.warnings.map((item) => `<li>${item}</li>`).join("");
  drawWealth(result.series, real, result.markers);
  drawLoan(result.series, result.markers);
  drawFlows(result.cashflow || [], real, result.markers);
}

function drawWealth(series, real, markers) {
  const buyKey = real ? "buy_real" : "buy_nominal";
  const rentKey = real ? "rent_real" : "rent_nominal";
  const etfKey = real ? "buy_etf_real" : "buy_etf_nominal";
  const values = series.flatMap((point) => [point[buyKey], point[rentKey], point[etfKey]]);
  paintChart(document.getElementById("wealth"), series, [
    [buyKey, "buy"],
    [rentKey, "rent"],
    [etfKey, "etf"],
  ], values, 210, "wealth", markers);
}

function drawLoan(series, markers) {
  const values = series.map((point) => point.loan_balance);
  paintChart(document.getElementById("loan"), series, [["loan_balance", "loan"]], values, 150, "loan", markers);
}

const RENT_FLOW = [
  ["rent_housing", "Miete", "#2a62b5"],
  ["rent_etf", "ETF", "#6d28d9"],
  ["rent_left", "Übrig", "#94a3b8"],
];
const BUY_FLOW = [
  ["buy_rent", "Miete", "#2a62b5"],
  ["buy_interest", "Zinsen", "#c2410c"],
  ["buy_principal", "Tilgung", "#0c8f62"],
  ["buy_owner", "Eigentümerkosten", "#d97706"],
  ["buy_etf", "ETF", "#6d28d9"],
  ["buy_left", "Übrig", "#94a3b8"],
];

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

function paintStack(svg, legend, points, layers, drawKey, real, markers, chartKey) {
  if (!svg) return;
  const shown = layers.filter((layer) => points.some((point) => flowAmount(point, layer[0], real) > 1));
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
  const rows = points.map((point) => shown.map((layer) => Math.max(0, flowAmount(point, layer[0], real))));
  const totals = rows.map((row) => row.reduce((sum, value) => sum + value, 0));
  const draws = points.map((point) => Math.max(0, flowAmount(point, drawKey, real)));
  const scale = valueScale(0, Math.max(1, ...totals, ...draws));
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
  const areas = shown.map((layer, layerIndex) => {
    const upper = rows.map((row, index) => {
      const sum = row.slice(0, layerIndex + 1).reduce((total, value) => total + value, 0);
      return `${x(index).toFixed(1)},${y(sum).toFixed(1)}`;
    });
    const lower = rows.map((row, index) => {
      const sum = row.slice(0, layerIndex).reduce((total, value) => total + value, 0);
      return `${x(index).toFixed(1)},${y(sum).toFixed(1)}`;
    }).reverse();
    return `<path fill="${layer[2]}" fill-opacity="0.88" d="M${upper.join(" L")} L${lower.join(" L")} Z" />`;
  }).join("");
  const withdrawal = draw
    ? `<path class="flow-line" d="${draws.map((value, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(value).toFixed(1)}`).join(" ")}" />`
    : "";
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
    values: rows.map((row) => row[layerIndex]),
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
  svg.innerHTML = `<line class="axis" x1="${padX}" y1="${y(0)}" x2="${width - padX}" y2="${y(0)}" />${levels}${areas}${withdrawal}${ticks}${marks}
    <line class="hover-guide" visibility="hidden" />
    <rect class="hover-catch" x="${padX}" y="${band}" width="${width - padX * 2}" height="${plotHeight}" fill="transparent" />`;
  bindPlotHover(svg, { points, series, x, band, plotHeight });
}

function bindPlotHover(svg, state) {
  svg._plot = state;
  hidePlotTip(svg);
  if (svg.dataset.hoverBound) return;
  svg.dataset.hoverBound = "1";
  svg.addEventListener("pointermove", (event) => showPlotTip(svg, event));
  svg.addEventListener("pointerleave", () => hidePlotTip(svg));
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

function showPlotTip(svg, event) {
  const state = svg._plot;
  if (!state || !state.points.length) return;
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
  const guide = svg.querySelector(".hover-guide");
  const xPos = state.x(index).toFixed(1);
  guide.setAttribute("x1", xPos);
  guide.setAttribute("x2", xPos);
  guide.setAttribute("y1", state.band);
  guide.setAttribute("y2", state.band + state.plotHeight);
  guide.setAttribute("visibility", "visible");
  const year = state.points[index].date.slice(0, 4);
  const rows = state.series.map((item) => `<div class="tip-row" style="color:${tipColor(item.color)}">${item.label} ${euro.format(item.values[index])}</div>`).join("");
  const tip = plotTip(svg);
  tip.innerHTML = `<div class="tip-x">${year}</div>${rows}`;
  tip.hidden = false;
  const plot = svg.parentElement.getBoundingClientRect();
  const pointX = rect.left - plot.left + (state.x(index) / view.width) * rect.width;
  let left = pointX + 14;
  if (left + tip.offsetWidth > plot.width - 4) left = Math.max(4, pointX - tip.offsetWidth - 14);
  const top = Math.min(Math.max(4, event.clientY - plot.top - tip.offsetHeight - 10), plot.height - tip.offsetHeight - 4);
  tip.style.left = `${left}px`;
  tip.style.top = `${top}px`;
}

function hidePlotTip(svg) {
  svg.querySelector(".hover-guide")?.setAttribute("visibility", "hidden");
  const tip = svg.parentElement?.querySelector(".plot-tip");
  if (tip) tip.hidden = true;
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
    while (hits(left, left + marker.w, row)) row += 1;
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
  const colors = { buy: "#0c8f62", rent: "#2a62b5", loan: "#0c8f62", etf: "#6d28d9" };
  const lineLabels = { buy: "Kaufen", rent: "Mieten", loan: "Restschuld", etf: "ETF im Kauf" };
  const paths = specs.map(([key, klass]) => {
    const points = series.map((point, index) => `${x(index).toFixed(1)},${y(point[key]).toFixed(1)}`);
    const line = points.map((point, index) => `${index ? "L" : "M"}${point}`).join(" ");
    const area = `${line} L${x(series.length - 1).toFixed(1)},${y(0).toFixed(1)} L${x(0).toFixed(1)},${y(0).toFixed(1)} Z`;
    const color = colors[klass] || "#2a62b5";
    const fill = klass === "etf" ? "" : `<path fill="${color}" fill-opacity="0.14" d="${area}" />`;
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
    if (!ticks.some((tick) => Math.abs(tick.x - bound.x) < 36)) ticks.push(bound);
  }
  ticks.sort((a, b) => a.x - b.x);
  const kept = [];
  for (const tick of ticks) {
    if (!kept.length || tick.x - kept.at(-1).x >= 36) kept.push(tick);
    else if (tick.year === endYear) kept[kept.length - 1] = tick;
  }
  return kept;
}