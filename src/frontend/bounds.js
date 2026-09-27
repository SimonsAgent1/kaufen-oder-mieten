/* Chat and import bounds. Keep in step with buy_vs_rent.bounds. */
(function () {
  const YEAR_MIN = 1930;
  const YEAR_MAX = 2100;
  const RETIRE_MIN = 55;
  const RETIRE_MAX = 75;
  const CARE_MIN = 60;
  const CARE_MAX = 110;
  const CAPS = {
    gross: 1_000_000,
    depot: 5_000_000,
    cash: 5_000_000,
    spar: 50_000,
    rent: 20_000,
    price: 5_000_000,
    moveIn: 500_000,
    reserve: 5_000_000,
  };

  function monthOk(iso) {
    const year = Number(String(iso).slice(0, 4));
    return year >= YEAR_MIN && year <= YEAR_MAX;
  }

  function ageAt(birth, month) {
    const [by, bm] = birth.slice(0, 7).split("-").map(Number);
    const [my, mm] = month.slice(0, 7).split("-").map(Number);
    let years = my - by;
    if (mm < bm) years -= 1;
    return years;
  }

  function careMonth(birth, careAge) {
    const [y, m] = birth.slice(0, 7).split("-").map(Number);
    return `${y + careAge}-${String(m).padStart(2, "0")}-01`;
  }

  function validateMonth(iso, label) {
    if (!iso) return `${label}: Bitte Monat und Jahr eintragen.`;
    if (!monthOk(iso)) return `${label}: Jahr zwischen ${YEAR_MIN} und ${YEAR_MAX}.`;
    return null;
  }

  function validateEuro(value, cap, label, { allowZero = true } = {}) {
    if (value == null || !Number.isFinite(value)) return `${label}: Bitte einen Betrag eintragen.`;
    if (value < 0 || (!allowZero && value <= 0)) return `${label}: Bitte einen positiven Betrag eintragen.`;
    if (value > cap) return `${label}: Höchstens ${cap.toLocaleString("de-DE")} €.`;
    return null;
  }

  function validateTogether(sharing, month, asOf) {
    const base = validateMonth(month, "Zusammenziehen");
    if (base) return base;
    if (sharing === "yes" && month > asOf) return "Der Monat muss am Startmonat oder davor liegen.";
    if (sharing === "no" && month <= asOf) return "Der Monat muss nach dem Startmonat liegen.";
    return null;
  }

  function validateMarriage(choice, month, asOf) {
    const base = validateMonth(month, "Heirat");
    if (base) return base;
    if (choice === "yes" && month > asOf) return "Der Monat muss am Startmonat oder davor liegen.";
    if (choice === "future" && month <= asOf) return "Der Monat muss nach dem Startmonat liegen.";
    return null;
  }

  function validateAdultBirth(birth, asOf) {
    const base = validateMonth(birth, "Geburt");
    if (base) return base;
    if (birth > asOf) return "Der Geburtsmonat darf nicht nach dem Startmonat liegen.";
    return null;
  }

  function validateChildBirth(birth, olderBirth) {
    const base = validateMonth(birth, "Kind");
    if (base) return base;
    if (birth <= olderBirth) return "Der Geburtsmonat des Kindes muss nach dem der älteren Person liegen.";
    return null;
  }

  function validateWorkStart(work, birth, asOf) {
    const base = validateMonth(work, "Erster Arbeitsmonat");
    if (base) return base;
    if (work < birth) return "Der erste Arbeitsmonat darf nicht vor dem Geburtsmonat liegen.";
    if (work > asOf) return "Der erste Arbeitsmonat darf nicht nach dem Startmonat liegen.";
    return null;
  }

  function validateRetireAge(ageRaw, birth, asOf, retiredPath) {
    if (ageRaw === "" || ageRaw == null) return "Bitte das Renteneintrittsalter eintragen.";
    const age = Number(ageRaw);
    if (!Number.isInteger(age) || age < RETIRE_MIN || age > RETIRE_MAX) {
      return `Das Renteneintrittsalter muss zwischen ${RETIRE_MIN} und ${RETIRE_MAX} liegen.`;
    }
    const now = ageAt(birth, asOf);
    if (retiredPath) {
      if (age > now) return "Das Renteneintrittsalter darf das heutige Alter nicht überschreiten.";
    } else if (age <= now) {
      return "Das Renteneintrittsalter muss über dem heutigen Alter liegen.";
    }
    return null;
  }

  function validateHorizon(careAge, horizonAge, youngerBirth, asOf) {
    if (careAge === "" || horizonAge === "") return "Bitte Pflegealter und Endalter eintragen.";
    const care = Number(careAge);
    const end = Number(horizonAge);
    if (!Number.isInteger(care) || care < CARE_MIN || care > CARE_MAX) {
      return `Das Pflegealter muss zwischen ${CARE_MIN} und ${CARE_MAX} liegen.`;
    }
    if (!Number.isInteger(end) || end < 1 || end > 120) {
      return "Das Endalter muss zwischen 1 und 120 liegen.";
    }
    const youngerNow = ageAt(youngerBirth, asOf);
    if (end <= youngerNow) return "Das Endalter muss über dem heutigen Alter der jüngeren Person liegen.";
    if (end >= CARE_MIN && end <= care) return "Das Endalter muss über dem Pflegealter liegen.";
    if (youngerNow < care && careMonth(youngerBirth, care) <= asOf) {
      return "Der Pflegebeginn muss nach dem Startmonat liegen.";
    }
    return null;
  }

  function validateLeaveMonths(rawValues) {
    let sum = 0;
    for (const raw of rawValues) {
      if (raw === "") return "Bitte alle Monate eintragen.";
      const months = Number(raw);
      if (!Number.isInteger(months) || months < 0 || months > 12) {
        return "Elternzeit je Person ist höchstens zwölf Monate.";
      }
      sum += months;
    }
    if (sum !== 12) return "Die Monate müssen zusammen 12 ergeben.";
    return null;
  }

  window.scenarioBounds = {
    CAPS,
    validateMonth,
    validateEuro,
    validateTogether,
    validateMarriage,
    validateAdultBirth,
    validateChildBirth,
    validateWorkStart,
    validateRetireAge,
    validateHorizon,
    validateLeaveMonths,
  };
})();
