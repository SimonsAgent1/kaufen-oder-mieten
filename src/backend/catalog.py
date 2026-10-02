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
        "pot-surplus-after-shortfall",
        "pots.pot_surplus_after_shortfall",
        "Topf-Auszahlung nach Wohnkosten",
        "Auszahlung aus einem Topf minus der Lücke zwischen Wohnkosten und Einkommen, mindestens 0.",
        "Modellwahl",
        "10.000 € Auszahlung und 3.000 € Lücke → 7.000 € bleiben als Bargeld in Übrig.",
        assumption=(
            "Eine Topf-Auszahlung im Rentenmonat zählt in Übrig und bleibt Bargeld. "
            "Sie ist keine Sparrate und geht nicht ins ETF. "
            "Daraus werden Wohnkosten gezahlt, die die Rente nicht trägt."
        ),
    ),
    Rule(
        "bank-loan-obligation-chart",
        "mortgage.bank_loan_obligation_chart_value",
        "Restschuld im Chart",
        "Bank: Restschuld plus noch fällige Zinsen bis Tilgung oder Verkauf. Sollzins bis zur Zinsbindung, danach Anschlusszins und ggf. höhere Rate bis zur Pflege.",
        "Modellwahl",
        "100.000 €, 3 %, 2 % Tilgung, 12 Monate ohne Wechsel: Restschuld plus Zinsen über 12 Monate.",
        assumption=(
            "Die Restschuld-Linie zeigt Bankdarlehen und Darlehen der Eltern jeweils als Restschuld plus noch fällige Zinsen. "
            "Das Vermögen zieht nur die Restschuld ab. Die monatlichen Zinsen im Kauf-Chart sind die gezahlten Zinsen."
        ),
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
        "Kaufpreis mal Jahresanteil, geteilt durch 12. Der Jahresanteil steht im Szenario; die Monats-Euro folgen dem Kaufpreis.",
        "Modellwahl",
        "400.000 € mal 0,75 % im Jahr sind 250 € im Monat.",
        assumption=(
            "Eigentümerkosten sind Anteil des Kaufpreises im Jahr. "
            "Die Monats-Euro sind Kaufpreis mal Anteil, geteilt durch 12."
        ),
    ),
    Rule(
        "min-equity-share",
        "house.extra_equity_from_price",
        "Eigenkapitalanteil vor dem Kauf",
        "Zusätzliches Eigenkapital als Anteil des Kaufpreises, nur wenn die Wartebedingung an ist. Nebenkosten und Einzugskosten kommen dazu.",
        "Modellwahl",
        "400.000 € mal 15 % sind 60.000 €.",
        assumption=None,
    ),
    Rule(
        "alg-rate",
        "career.arbeitslosengeld_rate",
        "Satz Arbeitslosengeld",
        "60 % ohne Kind im Haushalt, 67 % mit Kind.",
        "§ 149 SGB III",
        "Mit Kind → 0,67.",
    ),
    Rule(
        "employment-month",
        "career.employment_for_month",
        "Einkommen im Monat mit Jobwechsel",
        "Jobsegmente, Arbeitslosigkeit mit Leistungsdauer, danach null bis zum nächsten Job.",
        "Modellwahl",
        "Ohne Zusatzangaben bleibt ein Gehalt mit Wachstum.",
    ),
    Rule(
        "job-employment-month",
        "career.job_employment_for_month",
        "Brutto aus Jobsegmenten",
        "Erstes Segment ab work_start, weitere ab Jobwechsel mit eigenem Wachstum.",
        "Modellwahl",
        "Ab Jobwechsel gilt nur das neue Brutto und Wachstum.",
    ),
    Rule(
        "alg-benefit",
        "career.arbeitslosengeld_benefit",
        "Arbeitslosengeld im Modell",
        "60 % des modellierten Nettos vor dem Beginn, 67 % mit Kind im Haushalt.",
        "§ 149 SGB III, Modellwahl",
        "3.000 € Netto ohne Kind → 1.800 € im Monat.",
    ),
    Rule(
        "alg-months",
        "career.arbeitslosengeld_months",
        "Dauer Arbeitslosengeld",
        "12 Monate unter 50 Jahren, danach 15, 18 oder 24 Monate ab 50, 55 oder 58.",
        "§ 147 SGB III, Modellwahl",
        "49 Jahre → 12 Monate.",
    ),
    Rule(
        "avd-monthly-growth",
        "pots.avd_monthly_growth_factor",
        "Wachstum Altersvorsorgedepot",
        "Der Stand wird jeden Monat mit der nominalen ETF-Rendite aus dem Schieberegler fortgeschrieben, ohne TER und ohne Vorabpauschale.",
        "Modellwahl",
        "8,7 % im Jahr → Faktor (1,087)^(1/12) pro Monat.",
    ),
    Rule(
        "avd-grundzulage",
        "pots.grundzulage_altersvorsorgedepot",
        "Grundzulage Altersvorsorgedepot",
        "50 % der eigenen Beiträge bis 360 €, danach 25 % bis 1.800 €, höchstens 540 € im Jahr.",
        "Altersvorsorgereformgesetz, Modell 2027",
        "1.200 € eigene Beiträge → 390 € Zulage.",
    ),
    Rule(
        "avd-kinderzulage",
        "pots.kinderzulage_altersvorsorgedepot",
        "Kinderzulage je Kind",
        "100 % der eigenen Beiträge, höchstens 300 € je Kind im Jahr.",
        "Altersvorsorgereformgesetz, Modell 2027",
        "500 € eigene Beiträge → 300 € je Kind.",
    ),
    Rule(
        "avd-guenstigerpruefung",
        "pots.avd_grundzulage_and_refund",
        "Günstigerprüfung Altersvorsorgedepot",
        "Entweder Grundzulage in den Topf oder eine Steuerersparnis aus Sonderausgaben bis 1.800 €, je nachdem was höher ist. Liegt die Ersparnis darüber, zahlt das Modell nur die Grundzulage als Erstattung und keine Zulage in den Topf.",
        "Altersvorsorgereformgesetz, Modell 2027",
        "1.200 € eigene Beiträge → 390 € Zulage im Topf, 0 € Steuerersparnis.",
    ),
    Rule(
        "avd-sonderausgaben",
        "pots.avd_sonderausgaben_tax_benefit",
        "Sonderausgaben Altersvorsorgedepot",
        "Steuerersparnis nur auf dem Sonderausgabenpfad der Günstigerprüfung.",
        "Altersvorsorgereformgesetz, Modell 2027",
        "1.200 € eigene Beiträge → 0 € Erstattung, weil die Zulage höher ist.",
    ),
    Rule(
        "avd-excess-contribution",
        "pots.avd_excess_contribution_tax",
        "Beiträge über 1.800 €",
        "Eigene Beiträge über 1.800 € im Jahr werden im Beitragsjahr wie eine geförderte Auszahlung besteuert.",
        "Altersvorsorgereformgesetz, Modell 2027",
        "200 € über 1.800 € erhöhen die Steuer wie 200 € geförderte Auszahlung.",
    ),
    Rule(
        "parent-gift-tax",
        "gifts.gift_tax_parents",
        "Schenkung der Eltern",
        "Eine Schenkung ist nicht einkommensteuerpflichtig. Der Betrag wird hälftig je Elternteil angesetzt. Je Elternteil gilt ein Freibetrag von 400.000 €. Darüber folgt Steuerklasse I nach § 19 ErbStG.",
        "§§ 16 Abs. 1 Nr. 2, 19 ErbStG",
        "20.000 € gesamt → 0 € Steuer. 900.000 € gesamt → 7.000 € Steuer.",
        assumption=(
            "Eine Schenkung der Eltern zählt nicht als Einkommen. Sie wird hälftig je Elternteil versteuert, "
            "jeweils mit 400.000 € Freibetrag. Ein Darlehen der Eltern bleibt Darlehen und ist nicht die Bankfinanzierung."
        ),
    ),
    Rule(
        "parent-gift-allowance",
        "gifts.gift_tax_one_parent",
        "Freibetrag je Elternteil",
        "400.000 € Freibetrag je Elternteil auf die Hälfte der Schenkung.",
        "§ 16 Abs. 1 Nr. 2 ErbStG",
        "10.000 € von einem Elternteil → 0 € Steuer.",
    ),
    Rule(
        "inheritance-tax-class-i",
        "gifts.inheritance_tax_class_i",
        "Steuerklasse I",
        "7 % auf die ersten 75.000 € des steuerpflichtigen Erwerbs, danach höhere Stufen nach § 19 ErbStG.",
        "§ 19 ErbStG",
        "50.000 € steuerpflichtig → 3.500 €.",
    ),
    Rule(
        "parent-support-cash",
        "gifts.parent_support_cash",
        "Geld von den Eltern",
        "Schenkung netto nach Erwerbsteuer und Darlehen der Eltern erhöhen das verfügbare Bargeld im Startmonat. Das Darlehen bleibt als Schuld bis zum Ende.",
        "Modellwahl",
        "20.000 € Schenkung → 20.000 € mehr Bargeld, 0 € Steuer.",
        assumption=(
            "Schenkung netto nach Erwerbsteuer und Darlehen der Eltern erhöhen das Bargeld im Startmonat. "
            "Die Schuld bleibt bis zum Horizont, sofern keine Tilgung eingestellt ist. "
            "Der Zinssatz ist ein Jahresanteil der Restschuld, monatlich gezahlt. "
            "Fehlende Zins- oder Tilgungssätze in einer Datei gelten als 0 %."
        ),
    ),
    Rule(
        "parent-loan-interest-remaining",
        "gifts.parent_loan_interest_remaining",
        "Noch fällige Zinsen, Darlehen der Eltern",
        "Monatlicher Zins mal verbleibende Monate bis zum Horizont. Bei 0 % Zins ist der Betrag 0.",
        "Modellwahl",
        "100.000 €, 3 % im Jahr, 24 Monate → 6.000 €.",
    ),
    Rule(
        "parent-loan-interest",
        "gifts.parent_loan_interest_monthly",
        "Zins auf Darlehen der Eltern",
        "Jahresanteil der ausstehenden Schuld, in zwölf gleichen Monatszahlungen.",
        "Modellwahl",
        "100.000 € Schuld und 3 % im Jahr → 250 € im Monat.",
        assumption=(
            "Der Zinssatz auf das Darlehen der Eltern ist ein Jahresanteil der Restschuld, monatlich gezahlt. "
            "Er senkt den Spielraum auf beiden Wegen. Er ist nicht der Sollzins der Bank. "
            "Ein Zinssatz unter einem Marktzins ist keine Schenkung."
        ),
    ),
    Rule(
        "parent-loan-principal",
        "gifts.parent_loan_principal_monthly",
        "Tilgung, Darlehen der Eltern",
        "Jahresanteil der ausstehenden Schuld, in zwölf gleichen Monatszahlungen. Zins und Tilgung erscheinen im Kaufweg unter Zinsen und Tilgung.",
        "Modellwahl",
        "100.000 € Schuld und 2 % Tilgung im Jahr → etwa 167 € im Monat.",
        assumption=(
            "Die anfängliche Tilgung auf das Darlehen der Eltern ist ein Jahresanteil der Restschuld, monatlich gezahlt. "
            "Bei 0 % bleibt die Schuld bis zum Horizont. Sie ist nicht die Banktilgung."
        ),
    ),
    Rule(
        "rent-while-living-tax",
        "house.rent_while_living_tax_monthly",
        "Miete im eigenen Haus",
        "Kaltmiete von Mitbewohnern ist Einkünfte aus Vermietung und Verpachtung und wird mit dem persönlichen Satz besteuert, nicht als Kapitalertrag.",
        "§ 21 EStG",
        "600 € Kaltmiete im Monat erhöhen das zu versteuernde Einkommen um 7.200 € im Jahr.",
        assumption=(
            "Kaltmiete im eigenen Haus erscheint im Chart nach Abzug der Einkommensteuer mit dem persönlichen Satz "
            "und zählt zu Übrig, nicht als Gehaltseinkommen. Der vermietete Teil ist von der Verkaufssteuer ausgenommen; "
            "dieser Lauf besteuert keinen Anteil am Verkaufsgewinn. AfA und Zinsaufteilung sind nicht modelliert."
        ),
    ),
    Rule(
        "lump-insurance-gain",
        "pots.lump_insurance_gain",
        "Gewinn Kapitalversicherung",
        "Auszahlung minus eingezahlte Beiträge.",
        "§ 20 Abs. 1 Nr. 6 EStG",
        "60.000 € Auszahlung, 40.000 € Beiträge → 20.000 € Gewinn.",
    ),
    Rule(
        "lump-insurance-tax",
        "pots.lump_insurance_tax",
        "Steuer Kapital- oder Einmalrente",
        "Mindestens zwölf Jahre und Auszahlung ab 62: halber Gewinn mit persönlichem Satz. Sonst 25 % plus Soli auf den ganzen Gewinn.",
        "§ 20 Abs. 1 Nr. 6 EStG",
        "20.000 € Gewinn unter zwölf Jahren → 25 % plus Soli.",
    ),
    Rule(
        "private-annuity-taxable",
        "pots.private_annuity_taxable_annual",
        "Ertragsanteil private Leibrente",
        "Ab 67 Jahren sind 17 % der Jahresrente steuerpflichtig.",
        "§ 22 Nr. 1 EStG",
        "12.000 € im Jahr → 2.040 € steuerpflichtig.",
    ),
    Rule(
        "private-annuity-tax",
        "pots.private_annuity_income_tax",
        "Steuer private Leibrente",
        "Der Ertragsanteil erhöht das zu versteuernde Einkommen; die zusätzliche Einkommensteuer plus Soli wird berechnet.",
        "§ 22 Nr. 1 EStG",
        "2.040 € Ertragsanteil erhöht die Steuerlast.",
    ),
    Rule(
        "promoted-payout-tax",
        "pots.promoted_payout_tax",
        "Steuer geförderter Auszahlung",
        "Die Auszahlung aus Riester oder Altersvorsorgedepot ist voll steuerpflichtig.",
        "§ 22 Nr. 5 EStG",
        "20.000 € Auszahlung erhöhen das zu versteuernde Einkommen um 20.000 €.",
    ),
    Rule(
        "pot-surrender-total",
        "pots.pot_surrender_total",
        "Rückkaufswerte der Töpfe",
        "Summe der eingetragenen Rückkaufswerte aktiver Töpfe bis zur Auszahlung.",
        "Modellwahl",
        "Zwei Töpfe mit 10.000 € und 5.000 € → 15.000 €.",
    ),
    Rule(
        "kinderzulage-total",
        "pots.kinderzulage_total",
        "Kinderzulage gesamt",
        "Kinderzulage je Kind mal Anzahl der Kinder unter 25 im Modell.",
        "Altersvorsorgereformgesetz, Modell 2027",
        "300 € je Kind, zwei Kinder → 600 €.",
    ),
    Rule(
        "comparison-rent-monthly",
        "house.comparison_rent_monthly",
        "Vergleichsmiete im Monat",
        "Vergleichskaltmiete in Euro von heute, einmal im Jahr mit der Mietsteigerung fortgeschrieben. Sie dient dem Kaufpreisfaktor, nicht dem Monatschart.",
        "Modellwahl",
        "1.200 € Kaltmiete und 0 % Mietsteigerung → 1.200 € im Monat.",
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
            if scenario.dwelling.rent_while_living:
                lines.append(
                    "Ausschließliche Eigennutzung des ganzen Hauses gilt nicht, solange Kaltmiete im eigenen Haus an ist."
                )
            elif scenario.exclusive_own_use_until_sale:
                lines.append(entry.assumption)
            else:
                lines.append(
                    "Eigennutzung von Kauf bis Verkauf ist aus. Die Verkaufssteuer folgt Haltedauer und Gewinn."
                )
        elif entry.id == "rent-while-living-tax":
            if scenario.dwelling.rent_while_living:
                lines.append(entry.assumption)
        elif entry.id == "parent-gift-tax":
            if scenario.parent_gift or scenario.parent_loan:
                lines.append(entry.assumption)
        elif entry.id == "parent-loan-interest":
            if scenario.parent_loan and scenario.parent_loan_rate > 0:
                lines.append(entry.assumption)
        elif entry.id == "parent-loan-principal":
            if scenario.parent_loan and scenario.parent_loan_tilgung > 0:
                lines.append(entry.assumption)
        elif entry.id == "bank-loan-obligation-chart":
            lines.append(entry.assumption)
        elif entry.id == "pot-surplus-after-shortfall":
            if any(
                adult.pots.capital_life
                or adult.pots.private_lump
                or adult.pots.private_annuity
                or adult.pots.riester
                or adult.pots.altersvorsorgedepot
                for adult in scenario.adults
            ):
                lines.append(entry.assumption)
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
