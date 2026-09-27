const MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"];

function asOfMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function padMonth(year, month) {
  return `${year}-${String(month).padStart(2, "0")}-01`;
}

function childBirthSet(child) {
  return Boolean(child?.birth && /^\d{4}-\d{2}/.test(String(child.birth)));
}

function addMonths(iso, count) {
  const [year, month] = iso.slice(0, 7).split("-").map(Number);
  const index = year * 12 + (month - 1) + count;
  return `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, "0")}-01`;
}

function monthField(prefix, value) {
  const hasValue = Boolean(value && /^\d{4}-\d{2}/.test(String(value)));
  const monthNum = hasValue ? Number(String(value).slice(5, 7)) : 0;
  const options = MONTHS.map((name, index) => {
    const selected = monthNum === index + 1 ? " selected" : "";
    return `<option value="${index + 1}"${selected}>${name}</option>`;
  }).join("");
  const year = hasValue ? String(value).slice(0, 4) : "";
  const monthLead = hasValue ? "" : `<option value="" selected disabled>Monat</option>`;
  return `<label>Monat<select name="${prefix}-month" required>${monthLead}${options}</select></label>
    <label>Jahr<input name="${prefix}-year" type="number" inputmode="numeric" min="1930" max="2100" value="${year}" required></label>`;
}

function readMonth(root, prefix) {
  const yearRaw = root.querySelector(`[name=${prefix}-year]`)?.value ?? "";
  const monthRaw = root.querySelector(`[name=${prefix}-month]`)?.value ?? "";
  if (yearRaw === "" || monthRaw === "") return null;
  const year = Number(yearRaw);
  const month = Number(monthRaw);
  if (!Number.isFinite(year) || !Number.isFinite(month)) return null;
  return padMonth(year, month);
}

function parseEuroInput(raw) {
  const cleaned = String(raw).replace(/\s/g, "").replace(/\./g, "").replace(/,/g, ".");
  if (cleaned === "" || cleaned === ".") return null;
  const value = Number(cleaned);
  return Number.isFinite(value) ? value : null;
}

function formatEuroInput(value) {
  if (value === null || value === undefined || value === "") return "";
  const n = Number(value);
  if (!Number.isFinite(n)) return "";
  return new Intl.NumberFormat("de-DE", { maximumFractionDigits: 0 }).format(Math.round(n));
}

function euroField(fieldName, label, value, { required = false } = {}) {
  const shown = value === null || value === undefined ? "" : formatEuroInput(value);
  const req = required ? " required" : "";
  return `<label>${label}<input name="${fieldName}" type="text" inputmode="numeric" data-euro="1"${req} value="${shown}"></label>`;
}

function readEuroField(root, name) {
  const input = root.querySelector(`[name="${name}"]`);
  if (!input) return null;
  return parseEuroInput(input.value);
}

function wireEuroFields(root) {
  root.querySelectorAll("[data-euro]").forEach((input) => {
    input.addEventListener("input", () => {
      const parsed = parseEuroInput(input.value);
      if (parsed == null) return;
      const caret = input.selectionStart;
      const before = input.value.length;
      input.value = formatEuroInput(parsed);
      const after = input.value.length;
      const next = Math.max(0, (caret ?? after) + (after - before));
      input.setSelectionRange(next, next);
    });
  });
}

function wireEnter(root) {
  root.querySelectorAll("input, select").forEach((field) => {
    field.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      const run = root.querySelector("#run");
      if (run) {
        run.click();
        return;
      }
      const weiter = root.querySelector("[data-next].primary, .chat-nav button.primary[data-next]");
      (weiter || root.querySelector("[data-next]"))?.click();
    });
  });
}

const STAY_ON_STEP = "__stay__";

function bounds() {
  return window.scenarioBounds;
}

function ageAt(birth, month) {
  const [by, bm] = birth.slice(0, 7).split("-").map(Number);
  const [my, mm] = month.slice(0, 7).split("-").map(Number);
  let years = my - by;
  if (mm < bm) years -= 1;
  return years;
}

const chat = {
  answers: {},
  cursor: 0,
  preset: null,
  linkDwelling: null,
  fromWohnungLink: false,
  hasProfile: false,
};

function blankAnswers() {
  return {
    adults: [],
    children: [],
    together: null,
    married: null,
    rents: {},
    extra: null,
    cash: null,
    price: null,
    bundesland: "Bayern",
    moveIn: null,
    careAge: null,
    horizonAge: null,
    etfMode: null,
    etfReserve: null,
  };
}

function steps() {
  const list = [{ id: "count", render: renderCount, read: readCount }];
  const count = chat.answers.count || 1;
  for (let index = 0; index < count; index += 1) {
    list.push({ id: `person-${index}`, render: () => renderPerson(index), read: () => readPerson(index) });
  }
  if (count === 2) {
    list.push({ id: "together", render: renderTogether, read: readTogether });
    list.push({ id: "married", render: renderMarried, read: readMarried });
  }
  list.push({ id: "children", render: renderChildren, read: readChildren });
  if ((chat.answers.children || []).some((child) => childBirthSet(child) && addMonths(child.birth, 14) > asOfMonth())) {
    list.push({ id: "leave", render: renderLeave, read: readLeave });
  }
  for (let index = 0; index < count; index += 1) {
    const birth = chat.answers.adults[index]?.birth;
    if (!birth) continue;
    if (ageAt(birth, asOfMonth()) < 67) {
      list.push({ id: `work-${index}`, render: () => renderWork(index), read: () => readWork(index) });
    } else {
      list.push({ id: `retire-${index}`, render: () => renderRetireAge(index), read: () => readRetireAge(index) });
    }
  }
  list.push({ id: "rent", render: renderRent, read: readRent });
  if (childrenOverlap(chat.answers.children || [])) {
    list.push({ id: "extra", render: renderExtra, read: readExtra });
  }
  if (!chat.preset && !chat.linkDwelling) list.push({ id: "dwelling", render: renderDwelling, read: readDwelling });
  else list.push({ id: "cash", render: renderCash, read: readCash });
  list.push({ id: "horizon", render: renderHorizon, read: readHorizon });
  list.push({ id: "church", render: renderChurch, read: readChurch });
  list.push({ id: "etf", render: renderEtf, read: readEtf });
  list.push({ id: "recap", render: renderRecap, read: () => {} });
  return list;
}

function childrenOverlap(children) {
  const spans = children
    .filter(childBirthSet)
    .map((child) => [child.birth, addMonths(child.birth, 20 * 12)]);
  for (let i = 0; i < spans.length; i += 1) {
    for (let j = i + 1; j < spans.length; j += 1) {
      if (spans[i][0] < spans[j][1] && spans[j][0] < spans[i][1]) return true;
    }
  }
  return false;
}

function host() {
  return document.getElementById("chat");
}

function showChat() {
  document.getElementById("gate").hidden = true;
  host().hidden = false;
  document.getElementById("results").hidden = true;
}

function showGate() {
  document.getElementById("gate").hidden = false;
  host().hidden = true;
  document.getElementById("results").hidden = true;
  document.getElementById("banner").hidden = true;
  renderGate();
}

function clearStep(id) {
  if (id === "recap") return;
  if (id === "horizon") {
    chat.answers.careAge = null;
    chat.answers.horizonAge = null;
    return;
  }
  if (id === "church") {
    (chat.answers.adults || []).forEach((adult) => {
      delete adult.church_tax;
    });
    return;
  }
  if (id === "etf") {
    chat.answers.etfMode = null;
    chat.answers.etfReserve = null;
    return;
  }
  if (id === "cash") {
    chat.answers.cash = null;
    return;
  }
  if (id === "dwelling") {
    chat.answers.price = null;
    chat.answers.bundesland = "Bayern";
    chat.answers.cash = null;
    chat.answers.moveIn = null;
    return;
  }
  if (id === "rent") chat.answers.rents = {};
  if (id === "leave") {
    (chat.answers.children || []).forEach((child) => {
      child.leave = undefined;
    });
  }
  if (id === "children") chat.answers.children = [];
  if (id === "married") {
    chat.answers.married = null;
    chat.answers.marriedChoice = null;
  }
  if (id === "together") {
    chat.answers.together = null;
    chat.answers.sharing = null;
  }
  if (id === "extra") {
    chat.answers.extra = null;
    chat.answers.extraChoice = null;
  }
  const work = id.match(/^work-(\d+)$/);
  if (work) {
    const adult = chat.answers.adults[Number(work[1])] || {};
    delete adult.gross;
    delete adult.work;
    delete adult.depot;
    delete adult.sparrate;
    delete adult.retire_age;
  }
  const retire = id.match(/^retire-(\d+)$/);
  if (retire) delete chat.answers.adults[Number(retire[1])]?.retire_age;
  const person = id.match(/^person-(\d+)$/);
  if (person) chat.answers.adults[Number(person[1])] = {};
  if (id === "count") {
    delete chat.answers.count;
    chat.answers.adults = [];
  }
}

function abandonStepsFrom(index) {
  const sequence = steps();
  for (let i = index; i < sequence.length; i += 1) clearStep(sequence[i].id);
}

function render() {
  const sequence = steps();
  if (chat.cursor >= sequence.length) chat.cursor = sequence.length - 1;
  const step = sequence[chat.cursor];
  host().innerHTML = step.render();
  host().querySelectorAll("[data-next]").forEach((button) => {
    button.addEventListener("click", () => {
      chat.clicked = button;
      forward(step);
    });
  });
  host().querySelector("#run")?.addEventListener("click", finish);
  host().querySelector("[data-back]")?.addEventListener("click", back);
  host().querySelector("[data-add-child]")?.addEventListener("click", () => {
    readChildren();
    if ((chat.answers.children || []).length >= 8) return;
    chat.answers.children.push({ birth: null });
    render();
  });
  host().querySelectorAll("[data-remove-child]").forEach((button) => {
    button.addEventListener("click", () => {
      readChildren();
      const index = Number(button.dataset.removeChild);
      chat.answers.children.splice(index, 1);
      render();
    });
  });
  host().querySelectorAll("[data-jump]").forEach((button) => {
    button.addEventListener("click", () => {
      const sequenceNow = steps();
      const index = sequenceNow.findIndex((item) => item.id === button.dataset.jump);
      if (index >= 0) {
        chat.cursor = index;
        abandonStepsFrom(index + 1);
        render();
      }
    });
  });
  wireEuroFields(host());
  wireEnter(host());
}

function forward(step) {
  const error = step.read();
  const note = host().querySelector(".form-error");
  if (error === STAY_ON_STEP) {
    if (note) note.textContent = "";
    render();
    return;
  }
  if (error) {
    if (note) note.textContent = error;
    return;
  }
  chat.cursor += 1;
  const sequence = steps();
  if (chat.cursor >= sequence.length) chat.cursor = sequence.length - 1;
  if (sequence[chat.cursor].id === "recap" && chat.cursor === sequence.length - 1 && host().querySelector("[data-run]")) {
    return;
  }
  render();
}

function back() {
  if (chat.cursor === 0) {
    showGate();
    return;
  }
  abandonStepsFrom(chat.cursor);
  chat.cursor -= 1;
  render();
}

function renderCount() {
  return `<h2>Für wie viele Erwachsene rechnen wir?</h2>
    <div class="choices">
      <button type="button" class="primary" data-next data-count="1">Eine Person</button>
      <button type="button" data-next data-count="2">Zwei Personen</button>
    </div>
    <div class="chat-nav"><button type="button" data-back>Zurück</button></div>`;
}

function readCount() {
  chat.answers.count = Number(chat.clicked?.dataset?.count || 1);
  chat.answers.adults = chat.answers.adults.slice(0, chat.answers.count);
  while (chat.answers.adults.length < chat.answers.count) chat.answers.adults.push({});
  return null;
}

function renderPerson(index) {
  const adult = chat.answers.adults[index] || {};
  const heading = index === 0
    ? "Wie sollst du in der Grafik heißen?"
    : "Wie soll die zweite Person in der Grafik heißen?";
  return `<h2>${heading}</h2>
    <label>Name<input name="label" value="${adult.label || ""}" autocomplete="off"></label>
    <p>Geburtsmonat</p>
    ${monthField("birth", adult.birth)}
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readPerson(index) {
  const adult = chat.answers.adults[index] || {};
  adult.label = host().querySelector("[name=label]").value.trim();
  adult.birth = readMonth(host(), "birth");
  const err = bounds()?.validateAdultBirth(adult.birth, asOfMonth());
  if (err) return err;
  chat.answers.adults[index] = adult;
  return null;
}

function renderTogether() {
  if (!chat.answers.sharing) {
    return `<h2>Wohnt ihr schon zusammen?</h2>
    <div class="choices">
      <button type="button" data-next data-sharing="yes">Ja</button>
      <button type="button" data-next data-sharing="no">Noch nicht</button>
    </div>
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button></div>`;
  }
  const prompt = chat.answers.sharing === "yes" ? "Seit wann?" : "Ab wann?";
  return `<h2>Wohnt ihr schon zusammen?</h2>
    <p>${prompt}</p>
    ${monthField("together", chat.answers.together)}
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readTogether() {
  if (!chat.answers.sharing) {
    const sharing = chat.clicked?.dataset?.sharing;
    if (!sharing) return "Bitte Ja oder Noch nicht wählen.";
    chat.answers.sharing = sharing;
    chat.answers.together = null;
    return STAY_ON_STEP;
  }
  chat.answers.together = readMonth(host(), "together");
  return bounds()?.validateTogether(chat.answers.sharing, chat.answers.together, asOfMonth());
}

function renderMarried() {
  if (!chat.answers.marriedChoice) {
    return `<h2>Seid ihr verheiratet?</h2>
    <div class="choices">
      <button type="button" data-next data-married="yes">Ja</button>
      <button type="button" data-next data-married="future">Noch nicht</button>
      <button type="button" data-next data-married="no">Nein</button>
    </div>
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button></div>`;
  }
  if (chat.answers.marriedChoice === "no") {
    return `<h2>Seid ihr verheiratet?</h2><p>Nein.</p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
  }
  const prompt = chat.answers.marriedChoice === "yes" ? "Seit wann?" : "Ab wann?";
  return `<h2>Seid ihr verheiratet?</h2>
    <p>${prompt}</p>
    ${monthField("married", chat.answers.married)}
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readMarried() {
  if (!chat.answers.marriedChoice) {
    const choice = chat.clicked?.dataset?.married;
    if (!choice) return "Bitte eine Antwort wählen.";
    chat.answers.marriedChoice = choice;
    if (choice === "no") {
      chat.answers.married = null;
      return null;
    }
    chat.answers.married = null;
    return STAY_ON_STEP;
  }
  if (chat.answers.marriedChoice === "no") return null;
  chat.answers.married = readMonth(host(), "married");
  return bounds()?.validateMarriage(chat.answers.marriedChoice, chat.answers.married, asOfMonth());
}

function renderChildren() {
  const rows = (chat.answers.children || [])
    .map(
      (child, index) =>
        `<div class="child-block"><p class="child-name">Kind ${index + 1}</p>${monthField(`child-${index}`, child.birth)}
        <div class="child-remove"><button type="button" class="quiet pill" data-remove-child="${index}">Entfernen</button></div></div>`,
    )
    .join("");
  return `<h2>Gibt es Kinder, schon geboren oder noch erwartet?</h2>
    <p>Höchstens acht Kinder.</p>
    <div id="child-list">${rows}</div>
    <div class="choices"><button type="button" data-add-child>Ein Kind hinzufügen</button></div>
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readChildren() {
  const children = [];
  const rows = host().querySelectorAll(".child-block");
  const olderBirth = chat.answers.adults.reduce(
    (best, adult) => (adult.birth && (!best || adult.birth < best) ? adult.birth : best),
    null,
  );
  for (let index = 0; index < rows.length; index += 1) {
    const row = rows[index];
    const birth = readMonth(row, `child-${index}`);
    const err = bounds()?.validateChildBirth(birth, olderBirth);
    if (err) return err;
    children.push({ birth, leave: chat.answers.children[index]?.leave });
  }
  chat.answers.children = children;
  return null;
}

function renderLeave() {
  const adults = chat.answers.adults;
  const blocks = chat.answers.children.map((child, index) => {
    if (!childBirthSet(child) || addMonths(child.birth, 14) <= asOfMonth()) return "";
    const inputs = adults.map((adult, adultIndex) => {
      const months = child.leave?.[adultIndex];
      const value = months === undefined ? "" : months;
      const name = adult.label || (adultIndex === 0 ? "Du" : "Zweite Person");
      return `<label>${name}<input name="leave-${index}-${adultIndex}" type="number" min="0" max="12" inputmode="numeric" value="${value}"></label>`;
    }).join("");
    return `<fieldset><p>Kind ${index + 1}, Geburt ${child.birth.slice(0, 7)}</p>${inputs}</fieldset>`;
  }).join("");
  return `<h2>Elternzeit</h2>
    <p>Für jedes Kind zwölf Monate ab der Geburt. Die Monate eines Kindes ergeben zusammen zwölf.</p>
    ${blocks}
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readLeave() {
  for (let index = 0; index < chat.answers.children.length; index += 1) {
    const child = chat.answers.children[index];
    if (!childBirthSet(child) || addMonths(child.birth, 14) <= asOfMonth()) continue;
    let sum = 0;
    const leave = [];
    const rawValues = [];
    for (let adultIndex = 0; adultIndex < chat.answers.adults.length; adultIndex += 1) {
      const raw = host().querySelector(`[name=leave-${index}-${adultIndex}]`).value;
      rawValues.push(raw);
      const months = Number(raw);
      leave[adultIndex] = months;
      sum += months;
    }
    const err = bounds()?.validateLeaveMonths(rawValues);
    if (err) return err;
    chat.answers.children[index].leave = leave;
  }
  return null;
}

function renderWork(index) {
  const adult = chat.answers.adults[index];
  const name = adult.label || (index === 0 ? "Du" : "Zweite Person");
  const gross = adult.gross === undefined ? "" : adult.gross;
  const depot = adult.depot === undefined ? "" : adult.depot;
  const sparrate = adult.sparrate === undefined ? "" : adult.sparrate;
  const retire = adult.retire_age === undefined ? "" : adult.retire_age;
  return `<h2>${name}</h2>
    <p>Einkommen und Sparen.</p>
    ${euroField("gross", "Jahresbrutto in Euro", gross, { required: true })}
    <p>Erster Monat mit Arbeit</p>
    ${monthField("work", adult.work)}
    ${euroField("depot", "Depot heute, in Euro", depot, { required: true })}
    ${euroField("sparrate", "Sparrate im Monat, in Euro", sparrate, { required: true })}
    <label>Renteneintrittsalter<input name="retire" type="number" inputmode="numeric" min="55" max="75" value="${retire}" required></label>
    <p class="note">67 ist die Regelaltersgrenze für Geburten ab 1964, nicht automatisch dein Eintrittsalter.</p>
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readWork(index) {
  const adult = chat.answers.adults[index];
  const gross = readEuroField(host(), "gross");
  const depot = readEuroField(host(), "depot");
  const spar = readEuroField(host(), "sparrate");
  const retireRaw = host().querySelector("[name=retire]").value;
  const b = bounds();
  if ([gross, depot, spar].some((value) => value == null)) return "Bitte alle Felder ausfüllen.";
  let err = b?.validateEuro(gross, b.CAPS.gross, "Jahresbrutto");
  if (err) return err;
  err = b?.validateEuro(depot, b.CAPS.depot, "Depot");
  if (err) return err;
  err = b?.validateEuro(spar, b.CAPS.spar, "Sparrate");
  if (err) return err;
  adult.gross = gross;
  adult.work = readMonth(host(), "work");
  err = b?.validateWorkStart(adult.work, adult.birth, asOfMonth());
  if (err) return err;
  adult.depot = depot;
  adult.sparrate = spar;
  err = b?.validateRetireAge(retireRaw, adult.birth, asOfMonth(), false);
  if (err) return err;
  adult.retire_age = Number(retireRaw);
  return null;
}

function renderRetireAge(index) {
  const adult = chat.answers.adults[index];
  const name = adult.label || (index === 0 ? "Du" : "Zweite Person");
  const retire = adult.retire_age === undefined ? "" : adult.retire_age;
  return `<h2>${name}</h2>
    <p>Du bist schon im Rentenalter. Ab welchem Alter warst du in Rente?</p>
    <label>Renteneintrittsalter<input name="retire" type="number" inputmode="numeric" min="55" max="75" value="${retire}" required></label>
    <p class="note">67 ist die Regelaltersgrenze für Geburten ab 1964.</p>
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readRetireAge(index) {
  const adult = chat.answers.adults[index];
  const retireRaw = host().querySelector("[name=retire]").value;
  const err = bounds()?.validateRetireAge(retireRaw, adult.birth, asOfMonth(), true);
  if (err) return err;
  adult.retire_age = Number(retireRaw);
  return null;
}

function renderRent() {
  const two = chat.answers.count === 2;
  const future = two && chat.answers.together && chat.answers.together > asOfMonth();
  let fields = "";
  const solo = chat.answers.rents.solo === undefined ? "" : chat.answers.rents.solo;
  const rentA = chat.answers.rents.a === undefined ? "" : chat.answers.rents.a;
  const rentB = chat.answers.rents.b === undefined ? "" : chat.answers.rents.b;
  const shared = chat.answers.rents.shared === undefined ? "" : chat.answers.rents.shared;
  if (!two) {
    fields = euroField("rent-0", "Kaltmiete im Monat, in Euro", solo, { required: true });
  } else if (future) {
    fields = `${euroField("rent-0", "Kaltmiete der ersten Person", rentA, { required: true })}
      ${euroField("rent-1", "Kaltmiete der zweiten Person", rentB, { required: true })}
      ${euroField("shared", "Gemeinsame Kaltmiete ab dem Zusammenziehen", shared, { required: true })}`;
  } else {
    fields = euroField("shared", "Gemeinsame Kaltmiete", shared, { required: true });
  }
  return `<h2>Wie hoch ist die Kaltmiete?</h2>${fields}
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readRent() {
  const two = chat.answers.count === 2;
  const future = two && chat.answers.together && chat.answers.together > asOfMonth();
  const b = bounds();
  if (!two) {
    const raw = readEuroField(host(), "rent-0");
    const err = b?.validateEuro(raw, b.CAPS.rent, "Kaltmiete", { allowZero: true });
    if (err) return err;
    chat.answers.rents.solo = raw;
  } else if (future) {
    const a = readEuroField(host(), "rent-0");
    const rentB = readEuroField(host(), "rent-1");
    const shared = readEuroField(host(), "shared");
    for (const [value, label] of [
      [a, "Kaltmiete"],
      [rentB, "Kaltmiete"],
      [shared, "Gemeinsame Kaltmiete"],
    ]) {
      const err = b?.validateEuro(value, b.CAPS.rent, label, { allowZero: true });
      if (err) return err;
    }
    chat.answers.rents.a = a;
    chat.answers.rents.b = rentB;
    chat.answers.rents.shared = shared;
  } else {
    const shared = readEuroField(host(), "shared");
    const err = b?.validateEuro(shared, b.CAPS.rent, "Gemeinsame Kaltmiete", { allowZero: true });
    if (err) return err;
    chat.answers.rents.shared = shared;
  }
  return null;
}

function renderExtra() {
  if (!chat.answers.extraChoice) {
    return `<h2>Wenn mehrere Kinder gleichzeitig Platz brauchen: zahlt ihr dann mehr Kaltmiete?</h2>
    <div class="choices">
      <button type="button" data-next data-extra="no">Nein</button>
      <button type="button" data-next data-extra="yes">Ja</button>
    </div>
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button></div>`;
  }
  if (chat.answers.extraChoice === "no") {
    return `<h2>Wenn mehrere Kinder gleichzeitig Platz brauchen: zahlt ihr dann mehr Kaltmiete?</h2>
    <p>Nein.</p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
  }
  const amount = chat.answers.extra?.amount;
  const age = chat.answers.extra?.age;
  return `<h2>Wenn mehrere Kinder gleichzeitig Platz brauchen: zahlt ihr dann mehr Kaltmiete?</h2>
    ${euroField("extra-amount", "Mehr Kaltmiete im Monat, in Euro von heute", amount, { required: true })}
    <label>Bis das jüngere Kind dieses Alter erreicht<input name="extra-age" type="number" min="1" max="25" value="${age === undefined ? "" : age}" required></label>
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readExtra() {
  if (!chat.answers.extraChoice) {
    const choice = chat.clicked?.dataset?.extra;
    if (!choice) return "Bitte Ja oder Nein wählen.";
    chat.answers.extraChoice = choice;
    if (choice === "no") {
      chat.answers.extra = null;
      return null;
    }
    return STAY_ON_STEP;
  }
  if (chat.answers.extraChoice === "no") {
    chat.answers.extra = null;
    return null;
  }
  const amount = readEuroField(host(), "extra-amount");
  const ageRaw = host().querySelector("[name=extra-age]").value;
  const b = bounds();
  let err = b?.validateEuro(amount, b.CAPS.rent, "Mehr Kaltmiete", { allowZero: true });
  if (err) return err;
  if (ageRaw === "") return "Bitte Betrag und Alter eintragen.";
  chat.answers.extra = {
    yes: true,
    amount,
    age: Number(ageRaw),
  };
  return null;
}

function renderDwelling() {
  const lands = (chat.laender || ["Bayern"]).map((name) => {
    const selected = name === (chat.answers.bundesland || "Bayern") ? " selected" : "";
    return `<option${selected}>${name}</option>`;
  }).join("");
  const price = chat.answers.price === null ? "" : chat.answers.price;
  const moveIn = chat.answers.moveIn === null ? "" : chat.answers.moveIn;
  const cash = chat.answers.cash === null ? "" : chat.answers.cash;
  return `<h2>Was kostet das Haus oder die Wohnung?</h2>
    ${euroField("price", "Kaufpreis in Euro", price, { required: true })}
    <label>Bundesland<select name="land">${lands}</select></label>
    ${euroField("move-in", "Einmalige Einzugskosten in Euro von heute (0 = keine)", moveIn, { required: true })}
    <p class="note">Zum Beispiel Instandsetzung, Küche oder Umzug. Sie werden zum Kaufmonat mit der Inflation angehoben, bar mit den Nebenkosten gezahlt und nicht finanziert.</p>
    ${euroField("cash", "Bargeld außerhalb des Depots, in Euro", cash, { required: true })}
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readDwelling() {
  const price = readEuroField(host(), "price");
  const moveIn = readEuroField(host(), "move-in");
  const cash = readEuroField(host(), "cash");
  const b = bounds();
  let err = b?.validateEuro(price, b.CAPS.price, "Kaufpreis", { allowZero: false });
  if (err) return err;
  err = b?.validateEuro(moveIn, b.CAPS.moveIn, "Einzugskosten", { allowZero: true });
  if (err) return err;
  err = b?.validateEuro(cash, b.CAPS.cash, "Bargeld", { allowZero: true });
  if (err) return err;
  if ([price, moveIn, cash].some((value) => value == null)) return "Bitte alle Felder ausfüllen.";
  chat.answers.price = price;
  chat.answers.bundesland = host().querySelector("[name=land]").value;
  chat.answers.cash = cash;
  chat.answers.moveIn = moveIn;
  return null;
}

function renderCash() {
  const cash = chat.answers.cash === null ? "" : chat.answers.cash;
  return `<h2>Bargeld außerhalb des Depots</h2>
    <p>Nicht im ETF, aber für Nebenkosten oder den Kauf.</p>
    ${euroField("cash", "Betrag in Euro", cash, { required: true })}
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readCash() {
  const cash = readEuroField(host(), "cash");
  const err = bounds()?.validateEuro(cash, bounds().CAPS.cash, "Betrag", { allowZero: true });
  if (err) return err;
  chat.answers.cash = cash;
  return null;
}

function renderHorizon() {
  const care = chat.answers.careAge === null ? "" : chat.answers.careAge;
  const horizon = chat.answers.horizonAge === null ? "" : chat.answers.horizonAge;
  return `<h2>Wie weit soll die Rechnung gehen?</h2>
    <p>Haus oder Wohnung wird zum Beginn der Pflege verkauft. Das Endalter gilt für die jüngere Person.</p>
    <label>Alter bei Pflegebeginn<input name="care" type="number" min="60" max="110" value="${care}" required></label>
    <label>Alter am Ende der Rechnung<input name="horizon" type="number" min="1" max="120" value="${horizon}" required></label>
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readHorizon() {
  const careRaw = host().querySelector("[name=care]").value;
  const horizonRaw = host().querySelector("[name=horizon]").value;
  if ([careRaw, horizonRaw].some((value) => value === "")) return "Bitte Pflegealter und Endalter eintragen.";
  const youngerBirth = chat.answers.adults[youngerIndex()].birth;
  const err = bounds()?.validateHorizon(careRaw, horizonRaw, youngerBirth, asOfMonth());
  if (err) return err;
  chat.answers.careAge = Number(careRaw);
  chat.answers.horizonAge = Number(horizonRaw);
  return null;
}

function renderChurch() {
  const rows = chat.answers.adults.map((adult, index) => {
    const name = adult.label || (index === 0 ? "Du" : "Zweite Person");
    const on = adult.church_tax ? "checked" : "";
    return `<label class="switch church-row"><input type="checkbox" name="church-${index}" ${on}><span class="track"></span><span class="switch-text">${name}</span></label>`;
  }).join("");
  return `<h2>Kirchensteuer</h2>
    <p>Aus, bis ihr sie für eine Person einschaltet. Sie ist ein Anteil der Lohnsteuer: 8 % in Bayern und Baden-Württemberg, 9 % sonst.</p>
    ${rows}
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readChurch() {
  chat.answers.adults.forEach((adult, index) => {
    adult.church_tax = Boolean(host().querySelector(`[name=church-${index}]`)?.checked);
  });
  return null;
}

function renderEtf() {
  if (!chat.answers.etfMode) {
    return `<h2>Depot nach der Rente</h2>
    <p>Halten wächst den heutigen realen Wert um 0,5 % pro Jahr. Abbauen senkt ihn bis zum Horizont auf den Rest.</p>
    <div class="choices">
      <button type="button" data-next data-etf="hold">Den Wert halten</button>
      <button type="button" data-next data-etf="draw">Bis zum Ende abbauen</button>
    </div>
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button></div>`;
  }
  if (chat.answers.etfMode === "hold") {
    return `<h2>Depot nach der Rente</h2>
    <p>Den Wert halten.</p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
  }
  const reserve = chat.answers.etfReserve === null ? 0 : chat.answers.etfReserve;
  return `<h2>Depot nach der Rente</h2>
    <p>Bis zum Ende abbauen.</p>
    ${euroField("reserve", "Welcher Betrag soll am Ende übrig bleiben, in Euro von heute?", reserve, { required: true })}
    <p class="form-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" data-next>Weiter</button></div>`;
}

function readEtf() {
  if (!chat.answers.etfMode) {
    const mode = chat.clicked?.dataset?.etf;
    if (!mode) return "Bitte eine Option wählen.";
    chat.answers.etfMode = mode;
    if (mode === "hold") {
      chat.answers.etfReserve = 0;
      return null;
    }
    chat.answers.etfReserve = chat.answers.etfReserve ?? 0;
    return STAY_ON_STEP;
  }
  if (chat.answers.etfMode === "hold") return null;
  const reserve = readEuroField(host(), "reserve");
  const err = bounds()?.validateEuro(reserve, bounds().CAPS.reserve, "Restbetrag", { allowZero: true });
  if (err) return err;
  chat.answers.etfReserve = reserve;
  return null;
}

function youngerIndex() {
  let best = 0;
  chat.answers.adults.forEach((adult, index) => {
    if (adult.birth > chat.answers.adults[best].birth) best = index;
  });
  return best;
}

function buildScenario() {
  const adults = chat.answers.adults.map((adult, index) => {
    const retired = ageAt(adult.birth, asOfMonth()) >= 67;
    const id = index === 0 ? "a1" : "a2";
    let kaltmiete = 0;
    if (chat.answers.count === 1) kaltmiete = chat.answers.rents.solo || 0;
    else if (chat.answers.together && chat.answers.together > asOfMonth()) {
      kaltmiete = index === 0 ? chat.answers.rents.a || 0 : chat.answers.rents.b || 0;
    }
    else kaltmiete = (chat.answers.rents.shared || 0) / chat.answers.count;
    return {
      id,
      label: adult.label || "",
      birth: adult.birth,
      work_start: retired ? null : adult.work || null,
      retire_age: adult.retire_age,
      care_age: chat.answers.careAge,
      gross_salary: retired ? 0 : adult.gross || 0,
      salary_growth: 0.02,
      depot: adult.depot || 0,
      sparrate: retired ? 0 : adult.sparrate || 0,
      pension_gross_today: null,
      kaltmiete,
      church_tax: Boolean(adult.church_tax),
    };
  });
  const children = (chat.answers.children || []).map((child, index) => ({
    id: `k${index + 1}`,
    birth: child.birth,
    room_until_age: 20,
    leave: (child.leave || []).map((months, adultIndex) => ({
      adult_id: adults[adultIndex].id,
      months,
    })).filter((item) => item.months > 0),
  }));
  let extra = null;
  if (chat.answers.extra?.yes && children.length) {
    const births = children.map((child) => child.birth).sort();
    const younger = births[births.length - 1];
    extra = {
      amount_2026: chat.answers.extra.amount,
      from: births[1] || births[0],
      until: addMonths(younger, chat.answers.extra.age * 12),
    };
  }
  const dwellingPreset = chat.preset || chat.linkDwelling;
  const dwelling = dwellingPreset
    ? {
        purchase_price: dwellingPreset.purchase_price,
        bundesland: dwellingPreset.bundesland,
        notary_rate: dwellingPreset.notary_rate ?? 0.02,
        broker_rate: dwellingPreset.broker_rate ?? 0.0357,
        owner_costs: dwellingPreset.owner_costs ?? 250,
        move_in_cost_2026: 0,
        min_equity: true,
      }
    : {
        purchase_price: chat.answers.price,
        bundesland: chat.answers.bundesland,
        move_in_cost_2026: chat.answers.moveIn || 0,
        min_equity: true,
      };
  const younger = adults[youngerIndex()];
  return {
    version: 1,
    as_of: asOfMonth(),
    adults,
    together_from: adults.length === 2 ? chat.answers.together : null,
    married_from: adults.length === 2 ? chat.answers.married : null,
    shared_kaltmiete: adults.length === 2 ? chat.answers.rents.shared || 0 : 0,
    children,
    extra_rent: extra,
    equity_cash: chat.answers.cash ?? 0,
    horizon: { adult_id: younger.id, age: chat.answers.horizonAge },
    care_copay_2026: null,
    dwelling,
    beliefs: {
      household_rate: true,
      sollzins: null,
      anschlusszins: null,
      etf_consume: chat.answers.etfMode === "draw" ? 1 : 0,
      etf_reserve: chat.answers.etfMode === "draw" ? (chat.answers.etfReserve ?? 0) : 0,
    },
  };
}

function renderRecap() {
  const scenario = buildScenario();
  const lines = [
    ["count", scenario.adults.length === 2 ? "Zwei Personen" : "Eine Person"],
    ...scenario.adults.map((adult, index) => [`person-${index}`, `${adult.label || (index ? "Zweite Person" : "Du")}, ${adult.birth.slice(0, 7)}`]),
  ];
  if (scenario.together_from) lines.push(["together", `Zusammen ab ${scenario.together_from.slice(0, 7)}`]);
  if (scenario.adults.length === 2) {
    lines.push([
      "married",
      scenario.married_from ? `Verheiratet ab ${scenario.married_from.slice(0, 7)}` : "Nicht verheiratet",
    ]);
  }
  const childCount = scenario.children.length;
  const childLine = childCount === 0 ? "Keine Kinder" : childCount === 1 ? "Ein Kind" : `${childCount} Kinder`;
  lines.push(["children", childLine]);
  const moveIn = scenario.dwelling.move_in_cost_2026
    ? `, Einzug ${Math.round(scenario.dwelling.move_in_cost_2026).toLocaleString("de-DE")} €`
    : "";
  lines.push([
    "dwelling",
    `Haus oder Wohnung ${Math.round(scenario.dwelling.purchase_price).toLocaleString("de-DE")} €, ${scenario.dwelling.bundesland}${moveIn}`,
  ]);
  lines.push(["horizon", `Ende mit ${scenario.horizon.age}, Pflege ab ${chat.answers.careAge}.`]);
  const churchOn = scenario.adults.filter((adult) => adult.church_tax).map((adult) => adult.label || "Person");
  lines.push(["church", churchOn.length ? `Kirchensteuer: ${churchOn.join(", ")}` : "Kirchensteuer aus"]);
  lines.push([
    "etf",
    chat.answers.etfMode === "draw"
      ? `Depot abbauen, Rest ${Math.round(chat.answers.etfReserve ?? 0).toLocaleString("de-DE")} €`
      : "Depot halten",
  ]);
  const items = lines.map(([id, text]) => `<li><span>${text}</span><button type="button" data-jump="${id}">Ändern</button></li>`).join("");
  return `<h2>Passt das?</h2><ul class="recap">${items}</ul>
    <p class="form-error" id="recap-error"></p>
    <div class="chat-nav"><button type="button" data-back>Zurück</button><button type="button" class="primary" id="run">Rechnen</button></div>`;
}

async function finish() {
  const scenario = buildScenario();
  const probe = await fetch("/api/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      ...scenario,
      beliefs: {
        ...scenario.beliefs,
        sollzins: scenario.beliefs.sollzins ?? 0.03,
        anschlusszins: scenario.beliefs.anschlusszins ?? 0.03,
      },
    }),
  });
  if (!probe.ok) {
    const payload = await probe.json().catch(() => ({}));
    const note = host().querySelector("#recap-error");
    if (note) note.textContent = payload.detail || "Die Eingaben sind unvollständig oder ungültig.";
    return;
  }
  window.scenarioStore.persistScenario(scenario);
  host().hidden = true;
  window.showScenario(scenario, false);
}

function dwellingPresetFromScenario(dwelling) {
  if (!dwelling) return null;
  return {
    purchase_price: dwelling.purchase_price,
    bundesland: dwelling.bundesland,
    notary_rate: dwelling.notary_rate,
    broker_rate: dwelling.broker_rate,
    owner_costs: dwelling.owner_costs,
  };
}

function startChatFromGate() {
  chat.answers = blankAnswers();
  if (chat.fromWohnungLink && chat.linkDwelling) {
    chat.preset = chat.linkDwelling;
  }
  chat.cursor = 0;
  window.scenarioStore.beginNewRow();
  showChat();
  render();
}

async function renderGate() {
  const gate = document.getElementById("gate");
  const rowsHost = document.getElementById("gate-rows");
  const rows = window.scenarioStore.loadRows();
  const rowButtons = rows
    .map(
      (row) =>
        `<div class="gate-row"><button type="button" class="gate-open" data-row="${row.id}">${row.label}</button>
        <button type="button" class="gate-remove" data-remove-row="${row.id}" aria-label="Entfernen">×</button></div>`,
    )
    .join("");
  rowsHost.innerHTML = rowButtons;
  gate.querySelector(".gate-open")?.focus();
  rowsHost.querySelectorAll(".gate-open").forEach((button) => {
    button.addEventListener("click", () => {
      const row = window.scenarioStore.getRow(button.dataset.row);
      if (!row) return;
      let scenario = structuredClone(row.scenario);
      if (chat.linkDwelling) scenario = window.scenarioStore.mergeLinkDwelling(scenario, chat.linkDwelling);
      window.scenarioStore.openRow(row.id);
      host().hidden = true;
      window.showScenario(scenario, false);
    });
  });
  rowsHost.querySelectorAll(".gate-remove").forEach((button) => {
    button.addEventListener("click", () => {
      window.scenarioStore.removeRow(button.dataset.removeRow);
      renderGate();
    });
  });
}

function wireGate() {
  document.getElementById("gate-new")?.addEventListener("click", () => startChatFromGate());
  document.getElementById("gate-demo")?.addEventListener("click", () => loadDemo());
  document.getElementById("gate-import")?.addEventListener("change", async (event) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    const loaded = await window.scenarioStore.readScenarioFile(file);
    window.scenarioStore.addRow(loaded);
    renderGate();
  });
}

async function loadDemo() {
  window.scenarioStore.clearActive();
  document.getElementById("gate").hidden = true;
  const scenario = await fetch("/api/demo").then((response) => response.json());
  host().hidden = true;
  window.showScenario(scenario, true);
}

async function loadProfile() {
  const response = await fetch("/api/profile");
  if (!response.ok) return;
  window.scenarioStore.clearActive();
  document.getElementById("gate").hidden = true;
  host().hidden = true;
  window.showScenario(await response.json(), false);
}

async function bootChat() {
  window.scenarioStore.migrateLegacy();
  await window.scenarioStore.ensureProfileRow(() => fetch("/api/profile"));
  chat.answers = blankAnswers();
  const defaults = await fetch("/api/defaults").then((response) => response.json());
  chat.laender = Object.keys(defaults.bundeslaender);
  chat.hasProfile = Boolean(window.scenarioStore.getRow(window.scenarioStore.PROFILE_ROW_ID));
  const packed = new URLSearchParams(location.search).get("wohnung");
  if (packed) {
    const response = await fetch(`/api/wohnung?data=${encodeURIComponent(packed)}`);
    if (response.ok) {
      chat.linkDwelling = await response.json();
      chat.fromWohnungLink = true;
      chat.preset = chat.linkDwelling;
    }
  }
  wireGate();
  showGate();
}

window.reopenChat = (scenario) => {
  chat.answers = blankAnswers();
  if (chat.fromWohnungLink) {
    chat.preset = dwellingPresetFromScenario(scenario.dwelling);
  } else {
    chat.preset = null;
  }
  chat.answers.count = scenario.adults.length;
  chat.answers.adults = scenario.adults.map((adult) => ({
    label: adult.label,
    birth: adult.birth,
    gross: adult.gross_salary,
    work: adult.work_start,
    depot: adult.depot,
    sparrate: adult.sparrate,
    retire_age: adult.retire_age,
    church_tax: Boolean(adult.church_tax),
  }));
  chat.answers.together = scenario.together_from;
  if (scenario.together_from) {
    chat.answers.sharing = scenario.together_from > asOfMonth() ? "no" : "yes";
  } else {
    chat.answers.sharing = null;
  }
  chat.answers.married = scenario.married_from;
  if (!scenario.married_from) {
    chat.answers.marriedChoice = "no";
  } else {
    chat.answers.marriedChoice = scenario.married_from > asOfMonth() ? "future" : "yes";
  }
  chat.answers.rents = {
    solo: scenario.adults[0]?.kaltmiete || 0,
    a: scenario.adults[0]?.kaltmiete || 0,
    b: scenario.adults[1]?.kaltmiete || 0,
    shared: scenario.shared_kaltmiete || 0,
  };
  chat.answers.children = (scenario.children || []).map((child) => ({
    birth: child.birth,
    leave: scenario.adults.map((adult) => child.leave?.find((item) => item.adult_id === adult.id)?.months || 0),
  }));
  chat.answers.extraChoice = scenario.extra_rent ? "yes" : "no";
  chat.answers.extra = scenario.extra_rent ? { yes: true, amount: scenario.extra_rent.amount_2026, age: 20 } : null;
  const consume = scenario.beliefs?.etf_consume ?? 0;
  chat.answers.etfMode = consume >= 1 ? "draw" : "hold";
  chat.answers.etfReserve = scenario.beliefs?.etf_reserve ?? 0;
  if (!scenario.adults.some((adult) => adult.church_tax) && scenario.beliefs?.church_tax) {
    chat.answers.adults.forEach((adult) => {
      adult.church_tax = true;
    });
  }
  chat.answers.price = scenario.dwelling.purchase_price;
  chat.answers.bundesland = scenario.dwelling.bundesland;
  chat.answers.moveIn = scenario.dwelling.move_in_cost_2026 || 0;
  chat.answers.cash = scenario.equity_cash ?? 0;
  chat.answers.careAge = scenario.adults[0]?.care_age ?? null;
  chat.answers.horizonAge = scenario.horizon?.age ?? null;
  chat.cursor = steps().findIndex((step) => step.id === "recap");
  showChat();
  render();
};

window.resetChat = () => {
  chat.answers = blankAnswers();
  chat.cursor = 0;
  if (chat.fromWohnungLink) chat.preset = chat.linkDwelling;
  else chat.preset = null;
  window.scenarioStore.clearActive();
  showGate();
};

window.showGate = showGate;

document.addEventListener("DOMContentLoaded", bootChat);
