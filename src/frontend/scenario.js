/* Browser scenario list, import, export, and the dwelling link. The link whitelist matches LINK_FIELDS in scenario.py. */
const LIST_KEY = "buy-vs-rent-scenarios";
const LEGACY_KEY = "buy-vs-rent-scenario";
const LEGACY_DEMO_KEY = "buy-vs-rent-demo";
const PROFILE_ROW_ID = "local-profile";
const PROFILE_DISMISSED_KEY = "buy-vs-rent-profile-dismissed";
const LINK_FIELDS = ["purchase_price", "bundesland", "notary_rate", "broker_rate", "owner_costs"];

window.CHURCH_TAX_CONSENT_TEXT =
  "Ich willige ausdrücklich ein, dass die Angabe zur Kirchensteuer-Mitgliedschaft für die Steuerberechnung dieser Person verwendet wird (Art. 9 Abs. 1 und Abs. 2 lit. a DSGVO).";

window.applyChurchTaxConsent = function applyChurchTaxConsent(adult) {
  if (adult.church_tax_consent == null) adult.church_tax_consent = false;
  if (!adult.church_tax_consent) adult.church_tax = false;
};

let activeRowId = null;
let pendingNew = false;

function rowLabel(scenario) {
  if (!scenario?.adults?.length) return "Haushalt";
  return scenario.adults.map((adult, index) => adult.label?.trim() || `Person ${index + 1}`).join(" und ");
}

function loadRows() {
  const raw = localStorage.getItem(LIST_KEY);
  if (!raw) return [];
  try {
    const rows = JSON.parse(raw);
    return Array.isArray(rows) ? rows : [];
  } catch {
    return [];
  }
}

function saveRows(rows) {
  localStorage.setItem(LIST_KEY, JSON.stringify(rows));
}

function migrateLegacy() {
  const legacy = localStorage.getItem(LEGACY_KEY);
  if (!legacy) return;
  const rows = loadRows();
  if (!rows.length) {
    try {
      const scenario = JSON.parse(legacy);
      rows.push({ id: crypto.randomUUID(), label: rowLabel(scenario), scenario });
      saveRows(rows);
    } catch {
      /* ignore broken legacy payload */
    }
  }
  localStorage.removeItem(LEGACY_KEY);
  localStorage.removeItem(LEGACY_DEMO_KEY);
}

function beginNewRow() {
  pendingNew = true;
  activeRowId = null;
}

function openRow(id) {
  pendingNew = false;
  activeRowId = id;
}

function clearActive() {
  pendingNew = false;
  activeRowId = null;
}

function addRow(scenario) {
  const id = crypto.randomUUID();
  const rows = loadRows();
  rows.push({ id, label: rowLabel(scenario), scenario: structuredClone(scenario) });
  saveRows(rows);
  return id;
}

function removeRow(id) {
  if (id === PROFILE_ROW_ID) {
    localStorage.setItem(PROFILE_DISMISSED_KEY, "1");
  }
  saveRows(loadRows().filter((row) => row.id !== id));
  if (activeRowId === id) activeRowId = null;
}

async function ensureProfileRow(fetchProfile) {
  if (localStorage.getItem(PROFILE_DISMISSED_KEY)) return;
  const rows = loadRows();
  if (rows.some((row) => row.id === PROFILE_ROW_ID)) return;
  const response = await fetchProfile();
  if (!response.ok) return;
  const scenario = await response.json();
  rows.unshift({
    id: PROFILE_ROW_ID,
    label: rowLabel(scenario),
    scenario,
    fromProfile: true,
  });
  saveRows(rows);
}

function getRow(id) {
  return loadRows().find((row) => row.id === id);
}

function persistScenario(scenario) {
  const payload = structuredClone(scenario);
  const rows = loadRows();
  if (pendingNew) {
    const id = crypto.randomUUID();
    rows.push({ id, label: rowLabel(payload), scenario: payload });
    saveRows(rows);
    activeRowId = id;
    pendingNew = false;
    return id;
  }
  if (activeRowId) {
    const row = rows.find((item) => item.id === activeRowId);
    if (row) {
      row.scenario = payload;
      row.label = rowLabel(payload);
      saveRows(rows);
      return activeRowId;
    }
  }
  return addRow(payload);
}

function saveOpenRow(scenario) {
  if (!activeRowId) return null;
  const payload = structuredClone(scenario);
  const rows = loadRows();
  const row = rows.find((item) => item.id === activeRowId);
  if (!row) return null;
  row.scenario = payload;
  row.label = rowLabel(payload);
  saveRows(rows);
  return activeRowId;
}

function dwellingLinkUrl(dwelling) {
  const payload = {};
  for (const key of LINK_FIELDS) {
    if (dwelling[key] != null) payload[key] = dwelling[key];
  }
  const body = btoa(JSON.stringify(payload)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${location.origin}${location.pathname}?wohnung=${body}`;
}

function mergeLinkDwelling(scenario, link) {
  if (!link) return scenario;
  const next = structuredClone(scenario);
  next.dwelling = {
    ...next.dwelling,
    purchase_price: link.purchase_price,
    bundesland: link.bundesland,
    notary_rate: link.notary_rate ?? next.dwelling.notary_rate,
    broker_rate: link.broker_rate ?? next.dwelling.broker_rate,
    owner_costs: link.owner_costs ?? next.dwelling.owner_costs,
  };
  return next;
}

function downloadScenario(scenario) {
  const blob = new Blob([JSON.stringify(scenario, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "szenario.json";
  link.click();
  URL.revokeObjectURL(link.href);
}

function scalar(value) {
  if (value === "null" || value === "~" || value === "") return null;
  if (value === "true") return true;
  if (value === "false") return false;
  if (/^-?\d+(\.\d+)?$/.test(value)) return Number(value);
  if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
    return value.slice(1, -1);
  }
  return value;
}

function parseYaml(source) {
  const lines = [];
  for (const raw of source.split(/\n/)) {
    if (!raw.trim() || raw.trim().startsWith("#")) continue;
    lines.push({ indent: raw.match(/^ */)[0].length, text: raw.trim() });
  }
  let index = 0;
  function parse(level) {
    if (index >= lines.length) return null;
    if (lines[index].text.startsWith("- ") && lines[index].indent === level) {
      const list = [];
      while (index < lines.length && lines[index].indent === level && lines[index].text.startsWith("- ")) {
        const content = lines[index].text.slice(2);
        const lineIndent = lines[index].indent;
        index += 1;
        if (content.includes(":")) {
          const split = content.indexOf(":");
          const item = {};
          const key = content.slice(0, split).trim();
          const value = content.slice(split + 1).trim();
          if (value) item[key] = scalar(value);
          while (index < lines.length && lines[index].indent > lineIndent) {
            const nested = parse(lines[index].indent);
            if (nested && typeof nested === "object" && !Array.isArray(nested)) Object.assign(item, nested);
            else item[key] = nested;
          }
          list.push(item);
        } else {
          list.push(scalar(content));
        }
      }
      return list;
    }
    const obj = {};
    while (index < lines.length && lines[index].indent === level && !lines[index].text.startsWith("- ")) {
      const split = lines[index].text.indexOf(":");
      const key = lines[index].text.slice(0, split).trim();
      const value = lines[index].text.slice(split + 1).trim();
      const lineIndent = lines[index].indent;
      index += 1;
      if (!value) {
        obj[key] = index < lines.length && lines[index].indent > lineIndent ? parse(lines[index].indent) : null;
      } else {
        obj[key] = scalar(value);
      }
    }
    return obj;
  }
  return lines.length ? parse(lines[0].indent) : null;
}

async function readScenarioFile(file) {
  const text = await file.text();
  const trimmed = text.trim();
  if (trimmed.startsWith("{")) return JSON.parse(trimmed);
  return parseYaml(text);
}

window.scenarioStore = {
  LIST_KEY,
  LINK_FIELDS,
  PROFILE_ROW_ID,
  ensureProfileRow,
  migrateLegacy,
  loadRows,
  saveRows,
  rowLabel,
  beginNewRow,
  openRow,
  clearActive,
  addRow,
  removeRow,
  getRow,
  persistScenario,
  saveOpenRow,
  mergeLinkDwelling,
  dwellingLinkUrl,
  downloadScenario,
  parseYaml,
  readScenarioFile,
};
