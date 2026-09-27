"""Named formulas. ``docs/rules.md`` is rendered from this list."""

from __future__ import annotations

from dataclasses import dataclass

from buy_vs_rent.law.de_2026 import child_rearing_entgeltpunkte, church_tax_rate
from buy_vs_rent.scenario import Scenario, child_rearing_adult_id, labels


@dataclass(frozen=True)
class Rule:
    id: str
    function: str
    title: str
    formula: str
    source: str
    worked: str
    assumption: str | None = None


ENTRIES: tuple[Rule, ...] = (
    Rule(
        "social-contributions",
        "law.de_2026.social_contributions",
        "Sozialversicherung",
        "Arbeitnehmeranteil: Renten- und Arbeitslosenversicherung bis zur RV-Grenze, Kranken- und Pflegeversicherung bis zur KV-Grenze.",
        "Beitragssätze 2026",
        "60.000 € brutto, Pflege 1,7 %: der Beitrag liegt unter dem Brutto.",
    ),
    Rule(
        "taxable-income",
        "law.de_2026.taxable_income",
        "Zu versteuerndes Einkommen",
        "Brutto minus Sozialversicherung minus Werbungskostenpauschale 1.230 €, mindestens 0.",
        "EStG, Pauschale 2026",
        "Brutto 0 € ergibt 0 €.",
    ),
    Rule(
        "income-tax",
        "law.de_2026.income_tax",
        "Einkommensteuer",
        "Tarif 2026 auf das zu versteuernde Einkommen. Die Tarifeckwerte wachsen mit der Inflation.",
        "EStG-Tarif 2026, Näherung",
        "0 € zu versteuerndes Einkommen ergibt 0 € Steuer.",
        assumption="Die Lohnsteuer ist eine Näherung zum Tarif 2026, kein Bescheid.",
    ),
    Rule(
        "solidarity",
        "law.de_2026.solidarity",
        "Solidaritätszuschlag",
        "5,5 % der Einkommensteuer oberhalb der Freigrenze 2026, in der Minderungszone höchstens 11,9 % des Überschusses. Mit Splitting gilt die doppelte Freigrenze.",
        "SolZG",
        "Bei 25.000 € Steuer liegt der Soli unter 5,5 % der Steuer.",
    ),
    Rule(
        "income-levy",
        "law.de_2026.income_levy",
        "Einkommensteuer plus Soli",
        "Tarif plus Solidaritätszuschlag. Mit Splitting wird die Hälfte besteuert und verdoppelt.",
        "EStG und SolZG",
        "0 € ergibt 0 €.",
    ),
    Rule(
        "church-tax",
        "law.de_2026.church_tax_rate",
        "Kirchensteuer",
        "8 % der Einkommensteuer in Bayern und Baden-Württemberg, sonst 9 %, je Person. "
        "Näherung: der Satz mal der eigenen Steuer auf dem Grundtarif. "
        "Kein Anteil an der Splittingsteuer, kein besonderes Kirchgeld.",
        "Länderrecht",
        "Bayern ergibt 0,08. Hessen ergibt 0,09.",
        assumption="Kirchensteuer",
    ),
    Rule(
        "annual-net",
        "law.de_2026.annual_net",
        "Nettolohn im Jahr",
        "Brutto minus Sozialversicherung minus Einkommensteuer minus Soli minus Kirchensteuer.",
        "Modell aus den Bausteinen oben",
        "Brutto 0 € ergibt 0 €.",
    ),
    Rule(
        "monthly-net",
        "law.de_2026.monthly_net",
        "Nettolohn im Monat",
        "Nettolohn im Jahr geteilt durch 12. Brutto 0 € ergibt 0 €.",
        "Modell",
        "Brutto 0 € ergibt 0 € im Monat.",
    ),
    Rule(
        "pension-deductions",
        "law.de_2026.pension_deductions",
        "Abzüge auf der Rente",
        "Kranken- und Pflegebeitrag des Rentners bis zur KV-Grenze, plus Werbungskostenpauschale 102 €.",
        "Beitragssätze und Pauschale 2026",
        "Die Pauschale ist 102 €, bevor die Inflation sie anhebt.",
    ),
    Rule(
        "net-pension",
        "law.de_2026.net_monthly_pension",
        "Nettorente im Monat",
        "Jahresrente minus Krankenbeitrag minus Einkommensteuer minus Soli minus Kirchensteuer, geteilt durch 12.",
        "Modell",
        "Brutto 0 € ergibt 0 €.",
    ),
    Rule(
        "kinderfreibetrag",
        "law.de_2026.kinder_freibetrag_refund",
        "Kinderfreibetrag",
        "Im Dezember: je Kind der anteilige Freibetrag (Monate mit Kindergeld durch 12), summiert. Nur wenn die Steuerersparnis darüber liegt, kommt die Differenz zum gezahlten Kindergeld ins Depot.",
        "EStG, Günstigerprüfung",
        "Bei 40.000 € und vier Monaten Kindergeld schlägt der volle Freibetrag nicht das gezahlte Kindergeld.",
    ),
    Rule(
        "elterngeld",
        "law.de_2026.elterngeld_month",
        "Elterngeld",
        "Unter 1.000 € steigt die Ersatzrate Richtung 100 %, von 1.000 € bis 1.200 € sind es 67 %, bis 1.240 € gleitet sie auf 65 %. Schwellen, Sockel und Deckel sind Euro von 2026 und wachsen. Plus Geschwisterbonus. 0 € über 175.000 € zu versteuerndem Einkommen. Diese Grenze wächst nicht.",
        "BEEG, Grenze 2026",
        "Nicht berechtigt ergibt 0 €.",
        assumption="Die Grenze von 175.000 € zu versteuerndem Einkommen für Elterngeld bleibt in Euro von 2026 und wächst nicht mit der Inflation.",
    ),
    Rule(
        "transfer-tax",
        "law.de_2026.transfer_tax_rate",
        "Grunderwerbsteuer",
        "Satz des Bundeslandes. Ein gesetzter Satz im Szenario ersetzt die Tabelle.",
        "Länder, Stand 2026",
        "Bayern ergibt 0,035.",
    ),
    Rule(
        "purchase-costs",
        "law.de_2026.purchase_costs",
        "Kaufnebenkosten",
        "Kaufpreis mal (Grunderwerbsteuer + Notar + Makler).",
        "Modell",
        "100.000 € mal 0,02 sind 2.000 €.",
    ),
    Rule(
        "pv-rate",
        "law.de_2026.employee_pv_rate",
        "Pflegeversicherung",
        "Arbeitnehmersatz. Kinderlos ab 23 Jahren plus 0,6 Punkte. Ab dem zweiten Kind unter 25 Jahren minus 0,25 Punkte, bis zum fünften.",
        "SGB XI, 2026",
        "Keine Kinder, Alter 30, ergibt den Satz plus 0,6 Punkte.",
    ),
    Rule(
        "initial-payment",
        "mortgage.initial_payment",
        "Annuität",
        "Restschuld mal (Sollzins + anfängliche Tilgung) geteilt durch 12.",
        "Annuitätendarlehen",
        "120.000 €, Zins 3 %, Tilgung 2 %: 500 € im Monat.",
    ),
    Rule(
        "step-month",
        "mortgage.step_month",
        "Monatszins",
        "Zins ist Restschuld mal Jahreszins geteilt durch 12. Tilgung ist Rate minus Zins. Die neue Restschuld ist die alte minus Tilgung.",
        "Annuitätendarlehen",
        "120.000 € bei 3 % kosten im ersten Monat 300 € Zins.",
    ),
    Rule(
        "balance-after",
        "mortgage.balance_after",
        "Restschuld nach Monaten",
        "Dieselbe Monatsrechnung, mehrfach. Sie bleibt bei 0 stehen.",
        "Modell, gleich step_month",
        "Rate 0 und Zins 0 lassen die Schuld stehen.",
    ),
    Rule(
        "payment-to-clear",
        "mortgage.payment_to_clear",
        "Rate bis zur Pflege",
        "Annuität, die die Restschuld in den verbleibenden Monaten auf 0 bringt. Bei Zins 0 ist es Restschuld geteilt durch Monate.",
        "Annuitätenformel",
        "1.200 € in 12 Monaten ohne Zins sind 100 € im Monat.",
    ),
    Rule(
        "closed-form-balance",
        "mortgage.closed_form_balance",
        "Restschuld, geschlossen",
        "Schuld mal Aufzinsung minus die aufgezinsten Raten. Nie unter 0.",
        "Annuitätenformel",
        "Ohne Zins ist es Schuld minus Rate mal Monate, mindestens 0.",
    ),
    Rule(
        "capital-gains",
        "etf.capital_gains_rate",
        "Abgeltungsteuer",
        "25 % plus 5,5 % Soli darauf, also 26,375 %. Kirchensteuer kommt hier nicht obendrauf.",
        "Abgeltungsteuer",
        "Der Satz ist 0,26375.",
        assumption=(
            "Die 8,7 % als Startwert sind der MSCI World in Euro von 2006 bis 2025, grob um die Quellensteuer auf Dividenden gekürzt. "
            "Zieh auf der Rendite nicht noch einmal 0,3 Prozentpunkte ab. Die TER kommt extra."
        ),
    ),
    Rule(
        "reset-allowance",
        "etf.Portfolio.reset_allowance",
        "Sparerpauschbetrag, neues Jahr",
        "Der verbrauchte Pauschbetrag wird 0. Der Betrag selbst wächst mit der Inflation.",
        "EStG, Modell der Fortschreibung",
        "Nach dem Zurücksetzen ist der Verbrauch 0 €.",
    ),
    Rule(
        "deposit",
        "etf.Portfolio.deposit",
        "Einzahlung und Verkauf",
        "Ein Betrag ab 0 erhöht Kurswert und Einstand. Ein negativer Betrag verkauft so viel, dass nach Steuer dieser Betrag übrig ist.",
        "Modell",
        "100 € auf ein leeres Depot ergeben 100 € Kurswert und 0 € Steuer.",
    ),
    Rule(
        "trim-to",
        "etf.Portfolio.trim_to",
        "Verkauf auf einen Kurswert",
        "Verkauft, bis der Kurswert das Ziel erreicht, und versteuert den Gewinnanteil.",
        "Modell",
        "Ziel gleich Kurswert verkauft nichts.",
    ),
    Rule(
        "trim-to-net",
        "etf.Portfolio.trim_to_net",
        "Verkauf auf einen Nettobetrag",
        "Sucht den Verkauf, nach dem die Auszahlung nach Steuer das Ziel trifft.",
        "Modell",
        "Ziel 0 verkauft nichts.",
    ),
    Rule(
        "grow-month",
        "etf.Portfolio.grow_month",
        "Monatliche Rendite",
        "Kurswert mal (1 + Rendite − TER) hoch 1/12.",
        "Modellwahl",
        "Rendite 0 und TER 0 lassen den Kurswert stehen.",
    ),
    Rule(
        "vorabpauschale",
        "etf.Portfolio.vorabpauschale_tax",
        "Vorabpauschale",
        "Basiszins mal 70 % auf den Kurswert zu Jahresbeginn, anteilig für Zugänge im Jahr, gedeckelt durch den Wertzuwachs. 30 % Teilfreistellung auf den Basisertrag, dann Sparerpauschbetrag, dann Abgeltungsteuer. Der Einstand steigt um diesen gedeckelten Betrag.",
        "InvStG",
        "Basiszins 0 ergibt 0 € Steuer; der Einstand steigt nicht.",
        assumption=(
            "Der Basiszins der Vorabpauschale startet beim veröffentlichten Satz. "
            "Über ein langes Leben ist der heutige Satz von 3,20 % ein hoher Steuerfall. "
            "Der Schieber ist für einen niedrigeren Satz auf lange Sicht."
        ),
    ),
    Rule(
        "liquidation",
        "etf.Portfolio.liquidation",
        "Verkauf am Ende",
        "Gewinn ist Kurswert minus Einstand. Davon 70 % steuerpflichtig, minus restlicher Pauschbetrag, mal Abgeltungsteuer.",
        "InvStG, Teilfreistellung 30 % für Aktienfonds",
        "Kurswert gleich Einstand ergibt 0 € Steuer.",
        assumption=(
            "Der ETF ist thesaurierend, mit 30 % Teilfreistellung. Steuer gilt auf nominale Gewinne. "
            "Der Sparerpauschbetrag wächst mit der Inflation: 1.000 €, und 2.000 € ab der Heirat."
        ),
    ),
    Rule(
        "wipe",
        "etf.Portfolio.wipe",
        "Depot leeren",
        "Kurswert, Einstand und Jahreszähler werden 0.",
        "Modell",
        "Danach ist der Kurswert 0 €.",
    ),
    Rule(
        "snapshot",
        "etf.Portfolio.snapshot",
        "Kopie des Depots",
        "Eine Kopie, damit ein Probeverkauf den echten Stand nicht ändert.",
        "Modell",
        "Die Kopie hat denselben Kurswert.",
    ),
    Rule(
        "owner-costs",
        "house.monthly_owner_costs",
        "Eigentümerkosten als Prozent",
        "Kaufpreis mal Satz im Jahr, geteilt durch 12. Der Eurobetrag im Szenario ist maßgeblich; der Prozentsatz folgt diesem Betrag.",
        "Modellwahl",
        "400.000 € mal 0,75 % im Jahr sind 250 € im Monat.",
        assumption=(
            "Eigentümerkosten im Monat sind der Eurobetrag aus dem Szenario. "
            "Der Prozentsatz ist Anteil des Kaufpreises im Jahr und folgt dem Eurobetrag."
        ),
    ),
    Rule(
        "comparison-cold-rent",
        "house.comparison_cold_rent_monthly",
        "Vergleichskaltmiete für den Kaufpreisfaktor",
        "Bei einer Person die eigene Kaltmiete in Euro von heute. Bei zwei Personen die gemeinsame Kaltmiete, auch vor dem Zusammenziehen. "
        "Ein Zuschlag für eine größere Wohnung zählt nicht.",
        "Modellwahl",
        "Zwei Personen mit gemeinsamer Kaltmiete 1.200 € und Zuschlag 200 €: 1.200 € im Monat für den Faktor.",
    ),
    Rule(
        "price-to-rent",
        "house.price_to_rent",
        "Kaufpreisfaktor",
        "Kaufpreis geteilt durch zwölf Monate Vergleichskaltmiete in Euro von heute.",
        "Modellwahl",
        "360.000 € bei 1.200 € Kaltmiete im Monat ergibt 25,0.",
        assumption=(
            "Der Kaufpreisfaktor nutzt die Kaltmiete des verglichenen Haushalts in Euro von heute. "
            "Bei zwei Personen die gemeinsame Kaltmiete, auch vor dem Zusammenziehen. "
            "Ein Zuschlag für eine größere Wohnung zählt nicht. "
            "Unter 20, 20 bis 25 und über 25 sind keine Empfehlung."
        ),
    ),
    Rule(
        "price-to-rent-band",
        "house.price_to_rent_band",
        "Kaufpreisfaktor-Band",
        "Unter 20, 20 bis 25 und über 25 sind im Modell nur eine Einordnung, keine Empfehlung.",
        "Modellwahl",
        "Faktor 24 → 20 bis 25.",
    ),
    Rule(
        "sale-gain",
        "house.sale_gain",
        "Gewinn beim Verkauf",
        "Verkaufspreis nach Verkaufskosten minus Kaufpreis minus Kaufnebenkosten. Einmalige Einzugskosten zählen nicht zu dieser Basis.",
        "§ 23 EStG, Modell der Kosten",
        "Verkauf 100, Kosten 0, Kauf 80, Nebenkosten 5: Gewinn 15.",
    ),
    Rule(
        "house-sale-tax",
        "house.house_sale_tax",
        "Steuer auf den Verkauf",
        "0 € bei ausschließlicher Eigennutzung von Kauf bis Verkauf, oder bei Eigennutzung im Verkaufsjahr und den zwei Jahren davor (Teiljahre zählen), oder bei mehr als zehn Jahren Haltedauer, oder bei Gewinn unter 0. Sonst die zusätzliche Einkommensteuer plus Soli.",
        "§ 23 EStG",
        "Gewinn 0 ergibt 0 € Steuer.",
    ),
    Rule(
        "owner-occupied",
        "house.owner_occupied_exemption",
        "Eigennutzung",
        "Ja: ausschließliche Eigennutzung von Kauf bis Verkauf, §23-Befreiung. Nein: nur Haltedauer über zehn Jahre oder kein Gewinn. Gesetzlich gilt auch Eigennutzung im Verkaufsjahr und in den zwei Kalenderjahren davor; ein Teil-Kalenderjahr zählt mit.",
        "§ 23 EStG",
        "Kauf Dezember 2020 und Verkauf Januar 2021 ist bei Ja befreit.",
        assumption="Auf dem Kaufweg wohnt das Modell ausschließlich selbst bis zum Verkauf.",
    ),
    Rule(
        "kindergeld-until-age",
        "law.de_2026.kindergeld_until_age",
        "Kindergeld bis",
        "Ja endet mit dem 25. Geburtstag. Nein endet mit 18, ohne Ausbildungs- und Einkommensprüfung.",
        "BKGG, Modellwahl für Nein",
        "Ja → 25, Nein → 18.",
    ),
    Rule(
        "child-rearing-points",
        "law.de_2026.child_rearing_entgeltpunkte",
        "Kindererziehungszeiten",
        "Ein Erwachsener erhält die Punkte für alle Kinder zusammen (Modellwahl). Geburt ab 01.01.1992: 36 Monate, drei Entgeltpunkte. Davor: 24 Monate, zwei. Elternzeit zählt keine Entgeltpunkte.",
        "§§ 56 Abs. 1, 249 und 70 Abs. 2 SGB VI",
        "Kind 1991-12-01 und Kind 2000-06-01 → 5 Entgeltpunkte.",
        assumption="Kindererziehungszeiten erhöhen die geschätzte Rente des gewählten Erwachsenen.",
    ),
    Rule(
        "kindergeld",
        "model.kindergeld",
        "Kindergeld",
        "259 € je Kind und Monat im Jahr 2026, mit der Inflation fortgeschrieben, bis zum gewählten Endalter. Die Heirat ist keine Voraussetzung.",
        "BKGG, Betrag 2026",
        "Ein Kind, ein Monat, ohne Inflation: 259 €.",
        assumption=(
            "Kindergeld ist 259 € je Kind und Monat im Jahr 2026, auch ohne Heirat. "
            "Im Dezember wird es gegen den Kinderfreibetrag geprüft. Ehegattensplitting gilt ab dem Heiratsmonat."
        ),
    ),
    Rule(
        "withdrawal",
        "model.withdrawal",
        "Entnahme",
        "Bei Erhalt bleibt der reale Wert und wächst um 0,5 % im Jahr. Bei vollem Verzehr sinkt der reale Wert bis zum Horizont auf das Restvermögen. Dazwischen mischt der Schieber beide Ziele.",
        "Modellwahl",
        "Verzehr 0 hält den realen Wert plus 0,5 % im Jahr.",
        assumption=(
            "Bei Erhalt wächst das Depot inflationsbereinigt um 0,5 % pro Jahr; das Restvermögen wird dann nicht genutzt."
        ),
    ),
    Rule(
        "withdrawal-drawdown",
        "model.withdrawal_drawdown",
        "Entnahme bis zum Horizont",
        "Bei vollem Verzehr sinkt der reale Depotwert bis zum Horizont auf das Restvermögen in Euro von heute.",
        "Modellwahl",
        "Verzehr 1 und Rest 0 senkt den realen Wert auf null am Horizont.",
        assumption="Bei vollem Verzehr sinkt es bis zum Horizont auf das Restvermögen in Euro von heute.",
    ),
)


def by_function() -> dict[str, Rule]:
    return {entry.function: entry for entry in ENTRIES}


def result_sentences(scenario: Scenario) -> list[str]:
    lines: list[str] = []
    for entry in ENTRIES:
        if entry.assumption is None:
            continue
        if entry.id == "church-tax":
            names = labels(scenario)
            enabled = [names[adult.id] for adult in scenario.adults if adult.church_tax]
            if not enabled:
                lines.append("Kirchensteuer ist für niemanden an.")
            else:
                rate = church_tax_rate(scenario.dwelling.bundesland)
                who = ", ".join(enabled)
                lines.append(
                    f"Kirchensteuer ist für {who} an: {rate * 100:.0f} % der jeweiligen Einkommensteuer "
                    f"({scenario.dwelling.bundesland})."
                )
        elif entry.id == "withdrawal":
            if scenario.beliefs.etf_consume < 1:
                lines.append(entry.assumption)
        elif entry.id == "withdrawal-drawdown":
            if scenario.beliefs.etf_consume > 0:
                lines.append(entry.assumption)
        elif entry.id == "kindergeld":
            if scenario.kindergeld_until_25:
                lines.append(entry.assumption)
            else:
                lines.append(
                    "Kindergeld endet im Modell mit 18, ohne Ausbildungs- und Einkommensprüfung ab 18."
                )
        elif entry.id == "child-rearing-points":
            if scenario.children:
                credit = child_rearing_adult_id(scenario)
                who = labels(scenario)[credit]
                points = child_rearing_entgeltpunkte(*(child.birth for child in scenario.children))
                lines.append(
                    f"Kindererziehungszeiten: {points:.0f} Entgeltpunkte für {who}, alle Kinder zusammen."
                )
        elif entry.id == "owner-occupied":
            if scenario.exclusive_own_use_until_sale:
                lines.append(entry.assumption)
            else:
                lines.append(
                    "Eigennutzung von Kauf bis Verkauf ist aus. Die Verkaufssteuer folgt Haltedauer und Gewinn."
                )
        else:
            lines.append(entry.assumption)
    return lines


def render_rules() -> str:
    blocks = [
        "# Rechenregeln",
        "",
        "Diese Seite entsteht aus dem Katalog im Programm. Dieselbe Quelle speist die Annahmen auf dem Ergebnis.",
        "",
        "Zeitpunkte des Haushalts, also Heirat, Rente und Pflege, stehen in `docs/model.md`.",
        "",
    ]
    for entry in ENTRIES:
        blocks.extend(
            [
                f"## {entry.title}",
                "",
                entry.formula,
                "",
                f"Quelle: {entry.source}.",
                "",
                f"Probe: {entry.worked}",
                "",
            ]
        )
    return "\n".join(blocks).rstrip() + "\n"


def render_rules_html() -> str:
    body = (
        render_rules()
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return (
        "<!DOCTYPE html><html lang=\"de\"><head><meta charset=\"utf-8\">"
        "<link rel=\"icon\" href=\"/favicon.svg\" type=\"image/svg+xml\">"
        "<title>Rechenregeln</title></head><body><pre>"
        f"{body}</pre></body></html>"
    )
