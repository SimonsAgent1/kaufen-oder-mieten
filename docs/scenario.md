# Szenario

Version 1. Unbekannte Felder werden abgelehnt. Die Datei ist YAML oder JSON.

`path_scope` ist `both`, `buy` oder `rent`. Es speichert, welche Seite im Chat schon mit echten Angaben durchlaufen wurde. Fehlt das Feld, gilt `both`. Bei `rent` darf `dwelling.purchase_price` fehlen; der Kaufpreis ist dann nicht Teil der Angaben. Bei `buy` oder `both` ist er Pflicht.

`as_of` ist der erste Tag eines Monats. Die Rechnung beginnt dort. Die Steuerfiguren bleiben die Näherung für 2026.

## Personen

`adults` enthält eine oder zwei Personen. Eine dritte Person lehnt der Prüfer ab, bis es dafür Steuerregeln gibt.

Jede Person hat `id`, `label`, `birth`, `work_start` (leer, wenn nie erwerbstätig), `retire_age` (67), `care_age` (75), `gross_salary`, `salary_growth` (0,02), `depot`, `sparrate`, `pension_gross_today` (leer heißt schätzen), `kaltmiete` für die Zeit vor dem gemeinsamen Haushalt, `church_tax` (aus) und `church_tax_consent` (aus). `church_tax` darf nur `true` sein, wenn `church_tax_consent` `true` ist. Ein altes `beliefs.church_tax` schaltet die Kirchensteuer nur für Erwachsene mit Einwilligung ein.

Optional `job_changes` und `unemployment` je Person: Jobwechsel ab einem Monat mit neuem Brutto und eigenem Wachstum; Arbeitslosigkeit mit modelliertem Arbeitslosengeld und Dauer nach Alter. Leer bleibt ein Gehalt mit einem Wachstum.

Optional `pots` je Person: Schalter und Rückkaufswerte für Kapitallebensversicherung, private Einmalrente, private Leibrente, Riester (175 € Grundzulage im Jahr) und Altersvorsorgedepot (eigene Beiträge ab 2027, Standard 1.800 € im Jahr). Alles aus, bis der Schalter an ist. Kein zweites ETF-Depot.

Ein leeres Label wird „Du“ oder „Zweite Person“. Die Rechnung verwendet die `id`.

`together_from` ist der Monat, ab dem zwei Personen zusammenwohnen. Bei einer Person bleibt es leer. `married_from` ist der Monat, ab dem Ehegattensplitting und der doppelte Sparerpauschbetrag gelten. Es darf leer bleiben und vor oder nach dem Zusammenziehen liegen. Kindergeld wartet nicht auf die Heirat.

`shared_kaltmiete` ist die Kaltmiete ab `together_from`.

## Kinder

`children` ist eine Liste, höchstens acht. Jedes Kind hat `id`, `birth` in der Vergangenheit oder Zukunft, `room_until_age` (20) und `leave`: eine Liste `{adult_id, months}`. Die Monate werden ab dem Geburtsmonat der Reihe nach vergeben und sind zusammen höchstens 14. Der Chat schlägt 12 vor.

`extra_rent` ist `{amount_2026, from, until}` oder leer. Der Betrag ist Euro von 2026 und gilt nur, solange dieser Weg noch mietet. Leer heißt kein Zuschlag.

## Haus oder Wohnung, Horizont, Annahmen

`kindergeld_until_25` (wahr) läuft Kindergeld bis 25; falsch endet es im Modell mit 18, ohne Ausbildungs- und Einkommensprüfung. `child_rearing_credit_adult_id` ist die `id` des Erwachsenen mit den Kindererziehungszeiten für alle Kinder; ohne Kinder leer. `exclusive_own_use_until_sale` (wahr) nimmt Eigennutzung von Kauf bis Verkauf an.

`equity_cash` ist Bargeld außerhalb der Depots. Beim Kauf zahlt es Nebenkosten und senkt den Kredit. Auf dem Mietweg wird es im Startmonat angelegt.

`parent_gift` und `parent_gift_amount` modellieren eine einmalige Schenkung der Eltern im Startmonat, hälftig je Elternteil mit je 400.000 € Freibetrag und Erwerbsteuer nach Steuerklasse I. `parent_loan` und `parent_loan_amount` sind ein zinsloses Darlehen der Eltern mit demselben Zeitpunkt; es bleibt als Schuld im Endvermögen. Beides ist aus, bis der Schalter an ist. Das ist nicht die Bankfinanzierung.

`horizon` ist `{adult_id, age}` und meint den Monat, in dem diese Person so alt wird. Fehlt das Feld, nimmt die Rechnung die jüngere Person mit 100.

`care_copay_2026` leer heißt 3.600 € bei einer Person und 5.800 € bei zwei. Das ist eine Illustration aus dem hessischen Heimkostenbild von 2026, kein Pflegeplan.

`dwelling` trägt `purchase_price`, `bundesland`, optional `transfer_tax`, `notary_rate` (0,02), `broker_rate` (0,0357), `selling_cost_rate` (0), `owner_costs` (Startwert in Euro, nur zum Ableiten des Jahresanteils), `owner_costs_rate` (Anteil des Kaufpreises pro Jahr; die Monats-Euro sind `Preis * Satz / 12`), `owner_cost_growth`, `appreciation`, `min_equity`, `min_equity_share` (0,15), optional `move_in_cost_2026` (0), `rent_while_living` (aus) und `rent_while_living_kalt` (600). Mit Kaltmiete im eigenen Haus gilt auf dem Kaufweg keine ausschließliche Eigennutzung des ganzen Hauses; die Miete ist §21-Einkommen. Einmalige Einzugskosten in Euro von 2026 werden zum Kaufmonat mit der Inflation angehoben, bar mit den Nebenkosten gezahlt, nicht finanziert und erhöhen nicht den Kaufpreis oder die §23-Basis. Ein Wohnungslink darf sie nicht setzen und darf `owner_costs` in Euro mitgeben. `min_equity` wahr wartet, bis Depot und Bargeld die Nebenkosten, die Einzugskosten und `min_equity_share` des Preises decken.

`beliefs` sind die Schieberegler und kommen nicht aus dem Chat: `rent_growth` (0,025), `etf_return` (0,087), `ter` (0,0015), `basiszins` (0,032), `inflation` (0,02), `etf_consume` (0 oder 1: halten oder bis zum Horizont abbauen), `etf_reserve` (0, nur bei Abbau), `tilgung` (0,02), `zinsbindung_years` (15), `household_rate` (wahr). `sollzins` und `anschlusszins` bleiben leer, bis sie angefasst werden. Leer heißt: der Server setzt den nominalen Bundesbank-Satz plus Beleihungsauslauf und, wenn gewünscht, den Haushaltsabschlag. Kirchensteuer steht pro Erwachsenem, nicht in `beliefs`.

Abgeleitet und nicht gespeichert: Rentenmonat, Pflegemonat, Kindergeld-Fenster, Horizontende, Rentenschätzung, Kaufmonat.

## Seite

Nach dem Chat steht die Kurzfassung oben. Darunter liegen die Schieberegler in eingeklappten Gruppen; die Diagramme folgen darunter. Kurze Annahmesätze stehen an (i) an den Reglern, wo es einen gibt. Namen, Geburtsdaten, Elternzeit, Renteneintrittsalter, Pflegealter, Horizont, Bargeld, gemeinsame Kaltmiete, Kirchensteuer pro Person, Depotwahl und Restvermögen kommen aus dem Chat. Die übrigen `beliefs` und Modellannahmen stehen auf den Reglern. Kaufpreis, Bundesland, Einzugskosten und Bargeld werden im Chat gefragt und stehen zusätzlich auf den Reglern. Hausgeld ist nur der Jahresanteil des Kaufpreises; die Monats-Euro folgen dem Kaufpreis. Der Eigenkapitalanteil vor dem Kauf ist ein eigener Schieberegler. Eine leere Rente bleibt eine Schätzung und heißt am Regler so.

Angezeigte Euro sind ganze Euro. Ein Prozentwert ist nur so fein wie der Schritt seines Reglers, ohne überzählige Nachkommastellen. Der Kaufpreisfaktor hat eine Nachkommastelle. In der Datei und in der Rechnung bleiben die ungerundeten Werte.
