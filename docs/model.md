# Rechnung

Die Formeln mit Quelle und Probezahlen stehen in [docs/rules.md](rules.md). Dieselbe Liste speist die Annahmen auf der Seite.

Der Monatslauf beginnt bei `as_of` und endet im Horizont. Was in einem Monat gilt, liest das Haushaltsmodul aus dem Szenario. Steuersätze und Rentenanker stehen im Paket Deutschland 2026.

Die Kaltmiete ist die der einen Person, oder die Summe beider, bis `together_from`, danach die gemeinsame Miete. Sie steigt einmal im Jahr mit `rent_growth`. `extra_rent` kommt in Euro von 2026 nur dazu, solange dieser Weg noch mietet und der Monat im Fenster liegt. Nach dem Kauf fällt der Zuschlag auf dem Kaufweg weg. Ohne Feld gibt es keinen Zuschlag. Für den Kaufpreisfaktor gilt die Vergleichskaltmiete (eine Person: eigene Kaltmiete, zwei Personen: gemeinsame Kaltmiete). Nach dem Kauf zählt dieselbe Vergleichsmiete auf dem Kaufweg als laufende Einnahme (Mietvorteil) in „Monatlich beim Kaufen“, solange das Haus nicht verkauft ist.

Kindergeld ist 259 € von 2026 je Kind unter 25, vom Geburtsmonat bis zum Monat vor dem 25. Geburtstag, auch ohne Heirat. Ausbildungs- und Einkommensprüfungen ab 18 sind nicht modelliert. Im Dezember wird je Kind das bisher gezahlte Kindergeld mit dem anteiligen Freibetrag für dieselben Monate verglichen, dann über alle Kinder summiert. Ehegattensplitting nur ab `married_from`.

Die Pflegeversicherung folgt der Zahl der Kinder unter 25. Ein kinderloser Erwachsener ab 23 zahlt 0,6 Punkte mehr. Ab dem zweiten Kind unter 25 sinkt der Anteil um 0,25 Punkte je weiterem Kind, bis zum fünften.

Elternzeit ersetzt in diesen Monaten den Lohnanteil durch Elterngeld und zählt keine Entgeltpunkte. Elterngeld nutzt die bisherige Formel, inklusive Geschwisterbonus, wenn ein anderes Kind unter drei ist. Die Grenze von 175.000 € wird nicht mit der Inflation angehoben.

Entgeltpunkte laufen ab `work_start` über den Lohnpfad. Kindererziehungszeiten erhöhen die Schätzung für einen gewählten Erwachsenen. Elternzeit zählt keine Punkte. Ein gesetztes `pension_gross_today` ersetzt die Schätzung.

Jede Person spart bis zu ihrem eigenen Rentenmonat. Die andere spart weiter. Kindergeld wird angelegt, solange noch jemand spart. Entnommen wird erst, wenn alle in Rente sind. Davor wächst das Depot nur. Der Regler mischt Erhalt (0,5 Prozent real) und Verzehr bis `etf_reserve` in Euro von heute am Horizont.

Pflege beginnt beim frühesten Pflegealter. War ein Haus oder eine Wohnung gekauft, wird es in dem Monat verkauft. Auf dem Kaufweg wohnt das Modell bis dahin ausschließlich selbst. Die Steuer prüft § 23 EStG: diese Eigennutzung von Kauf bis Verkauf, oder Eigennutzung im Verkaufsjahr und den zwei Kalenderjahren davor (Teiljahre zählen), oder mehr als zehn Jahre Haltedauer, setzt die Steuer auf 0. Ab dem Verkauf zahlen beide Wege den Eigenanteil, fortgeschrieben mit der Inflation, statt Miete. Ist der Anschlusszins so hoch, dass die alte Rate die Restschuld nicht bis zur Pflege tilgt, steigt die Rate aus dem Übrig.

Kaufzeitpunkt, Nebenkosten, die 15-Prozent-Schwelle, Zinsbindung und Anschlusszins lesen den Block `dwelling`. Einmalige Einzugskosten in Euro von 2026 werden zum Kaufmonat mit der Inflation angehoben, bar mit den Nebenkosten gezahlt, nicht finanziert, erhöhen nicht den Kaufpreis und stehen nicht in der §23-Basis beim Verkaufsgewinn.

Heizkosten, die Mieter und Eigentümer beide tragen, fehlen. Die Lohnsteuer ist eine Näherung, kein Bescheid.

Die Startwerte 2,5 Prozent für Miete und Wohnung liegen bewusst unter kurzen städtischen Aufholphasen. Der Darmstädter Mietspiegel stieg von 2014 bis 2026 von 8,19 € auf 11,81 € je Quadratmeter, etwa 3,1 Prozent im Jahr. Wiederverkaufte Eigentumswohnungen dort stiegen von 2006 bis 2024 von 1.716 € auf 4.876 € je Quadratmeter, etwa 6 Prozent im Jahr; dieses Fenster enthält den Zinsrückgang. Die Rechnung lässt den Preis mit der Miete laufen und macht die Wohnung nicht noch einmal teurer gegenüber der Miete. Das ist eine Begründung für den Startwert, nicht der Gegenstand der Rechnung. Die 8,7 Prozent ETF-Rendite sind der MSCI World in Euro von 2006 bis 2025, grob um die Quellensteuer auf Dividenden gekürzt.
