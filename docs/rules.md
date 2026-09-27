# Rechenregeln

Diese Seite entsteht aus dem Katalog im Programm. Dieselbe Quelle speist die Annahmen auf dem Ergebnis.

Zeitpunkte des Haushalts, also Heirat, Rente und Pflege, stehen in `docs/model.md`.

## Sozialversicherung

Arbeitnehmeranteil: Renten- und Arbeitslosenversicherung bis zur RV-Grenze, Kranken- und Pflegeversicherung bis zur KV-Grenze.

Quelle: Beitragssätze 2026.

Probe: 60.000 € brutto, Pflege 1,7 %: der Beitrag liegt unter dem Brutto.

## Zu versteuerndes Einkommen

Brutto minus Sozialversicherung minus Werbungskostenpauschale 1.230 €, mindestens 0.

Quelle: EStG, Pauschale 2026.

Probe: Brutto 0 € ergibt 0 €.

## Einkommensteuer

Tarif 2026 auf das zu versteuernde Einkommen. Die Tarifeckwerte wachsen mit der Inflation.

Quelle: EStG-Tarif 2026, Näherung.

Probe: 0 € zu versteuerndes Einkommen ergibt 0 € Steuer.

## Solidaritätszuschlag

5,5 % der Einkommensteuer oberhalb der Freigrenze 2026, in der Minderungszone höchstens 11,9 % des Überschusses. Mit Splitting gilt die doppelte Freigrenze.

Quelle: SolZG.

Probe: Bei 25.000 € Steuer liegt der Soli unter 5,5 % der Steuer.

## Einkommensteuer plus Soli

Tarif plus Solidaritätszuschlag. Mit Splitting wird die Hälfte besteuert und verdoppelt.

Quelle: EStG und SolZG.

Probe: 0 € ergibt 0 €.

## Kirchensteuer

8 % der Einkommensteuer in Bayern und Baden-Württemberg, sonst 9 %, je Person. Näherung: der Satz mal der eigenen Steuer auf dem Grundtarif. Kein Anteil an der Splittingsteuer, kein besonderes Kirchgeld.

Quelle: Länderrecht.

Probe: Bayern ergibt 0,08. Hessen ergibt 0,09.

## Nettolohn im Jahr

Brutto minus Sozialversicherung minus Einkommensteuer minus Soli minus Kirchensteuer.

Quelle: Modell aus den Bausteinen oben.

Probe: Brutto 0 € ergibt 0 €.

## Nettolohn im Monat

Nettolohn im Jahr geteilt durch 12. Brutto 0 € ergibt 0 €.

Quelle: Modell.

Probe: Brutto 0 € ergibt 0 € im Monat.

## Abzüge auf der Rente

Kranken- und Pflegebeitrag des Rentners bis zur KV-Grenze, plus Werbungskostenpauschale 102 €.

Quelle: Beitragssätze und Pauschale 2026.

Probe: Die Pauschale ist 102 €, bevor die Inflation sie anhebt.

## Nettorente im Monat

Jahresrente minus Krankenbeitrag minus Einkommensteuer minus Soli minus Kirchensteuer, geteilt durch 12.

Quelle: Modell.

Probe: Brutto 0 € ergibt 0 €.

## Kinderfreibetrag

Im Dezember: je Kind der anteilige Freibetrag (Monate mit Kindergeld durch 12), summiert. Nur wenn die Steuerersparnis darüber liegt, kommt die Differenz zum gezahlten Kindergeld ins Depot.

Quelle: EStG, Günstigerprüfung.

Probe: Bei 40.000 € und vier Monaten Kindergeld schlägt der volle Freibetrag nicht das gezahlte Kindergeld.

## Elterngeld

Unter 1.000 € steigt die Ersatzrate Richtung 100 %, von 1.000 € bis 1.200 € sind es 67 %, bis 1.240 € gleitet sie auf 65 %. Schwellen, Sockel und Deckel sind Euro von 2026 und wachsen. Plus Geschwisterbonus. 0 € über 175.000 € zu versteuerndem Einkommen. Diese Grenze wächst nicht.

Quelle: BEEG, Grenze 2026.

Probe: Nicht berechtigt ergibt 0 €.

## Grunderwerbsteuer

Satz des Bundeslandes. Ein gesetzter Satz im Szenario ersetzt die Tabelle.

Quelle: Länder, Stand 2026.

Probe: Bayern ergibt 0,035.

## Kaufnebenkosten

Kaufpreis mal (Grunderwerbsteuer + Notar + Makler).

Quelle: Modell.

Probe: 100.000 € mal 0,02 sind 2.000 €.

## Pflegeversicherung

Arbeitnehmersatz. Kinderlos ab 23 Jahren plus 0,6 Punkte. Ab dem zweiten Kind unter 25 Jahren minus 0,25 Punkte, bis zum fünften.

Quelle: SGB XI, 2026.

Probe: Keine Kinder, Alter 30, ergibt den Satz plus 0,6 Punkte.

## Annuität

Restschuld mal (Sollzins + anfängliche Tilgung) geteilt durch 12.

Quelle: Annuitätendarlehen.

Probe: 120.000 €, Zins 3 %, Tilgung 2 %: 500 € im Monat.

## Monatszins

Zins ist Restschuld mal Jahreszins geteilt durch 12. Tilgung ist Rate minus Zins. Die neue Restschuld ist die alte minus Tilgung.

Quelle: Annuitätendarlehen.

Probe: 120.000 € bei 3 % kosten im ersten Monat 300 € Zins.

## Restschuld nach Monaten

Dieselbe Monatsrechnung, mehrfach. Sie bleibt bei 0 stehen.

Quelle: Modell, gleich step_month.

Probe: Rate 0 und Zins 0 lassen die Schuld stehen.

## Rate bis zur Pflege

Annuität, die die Restschuld in den verbleibenden Monaten auf 0 bringt. Bei Zins 0 ist es Restschuld geteilt durch Monate.

Quelle: Annuitätenformel.

Probe: 1.200 € in 12 Monaten ohne Zins sind 100 € im Monat.

## Restschuld, geschlossen

Schuld mal Aufzinsung minus die aufgezinsten Raten. Nie unter 0.

Quelle: Annuitätenformel.

Probe: Ohne Zins ist es Schuld minus Rate mal Monate, mindestens 0.

## Abgeltungsteuer

25 % plus 5,5 % Soli darauf, also 26,375 %. Kirchensteuer kommt hier nicht obendrauf.

Quelle: Abgeltungsteuer.

Probe: Der Satz ist 0,26375.

## Sparerpauschbetrag, neues Jahr

Der verbrauchte Pauschbetrag wird 0. Der Betrag selbst wächst mit der Inflation.

Quelle: EStG, Modell der Fortschreibung.

Probe: Nach dem Zurücksetzen ist der Verbrauch 0 €.

## Einzahlung und Verkauf

Ein Betrag ab 0 erhöht Kurswert und Einstand. Ein negativer Betrag verkauft so viel, dass nach Steuer dieser Betrag übrig ist.

Quelle: Modell.

Probe: 100 € auf ein leeres Depot ergeben 100 € Kurswert und 0 € Steuer.

## Verkauf auf einen Kurswert

Verkauft, bis der Kurswert das Ziel erreicht, und versteuert den Gewinnanteil.

Quelle: Modell.

Probe: Ziel gleich Kurswert verkauft nichts.

## Verkauf auf einen Nettobetrag

Sucht den Verkauf, nach dem die Auszahlung nach Steuer das Ziel trifft.

Quelle: Modell.

Probe: Ziel 0 verkauft nichts.

## Monatliche Rendite

Kurswert mal (1 + Rendite − TER) hoch 1/12.

Quelle: Modellwahl.

Probe: Rendite 0 und TER 0 lassen den Kurswert stehen.

## Vorabpauschale

Basiszins mal 70 % auf den Kurswert zu Jahresbeginn, anteilig für Zugänge im Jahr, gedeckelt durch den Wertzuwachs. 30 % Teilfreistellung auf den Basisertrag, dann Sparerpauschbetrag, dann Abgeltungsteuer. Der Einstand steigt um diesen gedeckelten Betrag.

Quelle: InvStG.

Probe: Basiszins 0 ergibt 0 € Steuer; der Einstand steigt nicht.

## Verkauf am Ende

Gewinn ist Kurswert minus Einstand. Davon 70 % steuerpflichtig, minus restlicher Pauschbetrag, mal Abgeltungsteuer.

Quelle: InvStG, Teilfreistellung 30 % für Aktienfonds.

Probe: Kurswert gleich Einstand ergibt 0 € Steuer.

## Depot leeren

Kurswert, Einstand und Jahreszähler werden 0.

Quelle: Modell.

Probe: Danach ist der Kurswert 0 €.

## Kopie des Depots

Eine Kopie, damit ein Probeverkauf den echten Stand nicht ändert.

Quelle: Modell.

Probe: Die Kopie hat denselben Kurswert.

## Eigentümerkosten als Prozent

Kaufpreis mal Satz im Jahr, geteilt durch 12. Der Eurobetrag im Szenario ist maßgeblich; der Prozentsatz folgt diesem Betrag.

Quelle: Modellwahl.

Probe: 400.000 € mal 0,75 % im Jahr sind 250 € im Monat.

## Vergleichskaltmiete für den Kaufpreisfaktor

Bei einer Person die eigene Kaltmiete in Euro von heute. Bei zwei Personen die gemeinsame Kaltmiete, auch vor dem Zusammenziehen. Ein Zuschlag für eine größere Wohnung zählt nicht.

Quelle: Modellwahl.

Probe: Zwei Personen mit gemeinsamer Kaltmiete 1.200 € und Zuschlag 200 €: 1.200 € im Monat für den Faktor.

## Kaufpreisfaktor

Kaufpreis geteilt durch zwölf Monate Vergleichskaltmiete in Euro von heute.

Quelle: Modellwahl.

Probe: 360.000 € bei 1.200 € Kaltmiete im Monat ergibt 25,0.

## Kaufpreisfaktor-Band

Unter 20, 20 bis 25 und über 25 sind im Modell nur eine Einordnung, keine Empfehlung.

Quelle: Modellwahl.

Probe: Faktor 24 → 20 bis 25.

## Gewinn beim Verkauf

Verkaufspreis nach Verkaufskosten minus Kaufpreis minus Kaufnebenkosten. Einmalige Einzugskosten zählen nicht zu dieser Basis.

Quelle: § 23 EStG, Modell der Kosten.

Probe: Verkauf 100, Kosten 0, Kauf 80, Nebenkosten 5: Gewinn 15.

## Steuer auf den Verkauf

0 € bei ausschließlicher Eigennutzung von Kauf bis Verkauf, oder bei Eigennutzung im Verkaufsjahr und den zwei Jahren davor (Teiljahre zählen), oder bei mehr als zehn Jahren Haltedauer, oder bei Gewinn unter 0. Sonst die zusätzliche Einkommensteuer plus Soli.

Quelle: § 23 EStG.

Probe: Gewinn 0 ergibt 0 € Steuer.

## Eigennutzung

Ja: ausschließliche Eigennutzung von Kauf bis Verkauf, §23-Befreiung. Nein: nur Haltedauer über zehn Jahre oder kein Gewinn. Gesetzlich gilt auch Eigennutzung im Verkaufsjahr und in den zwei Kalenderjahren davor; ein Teil-Kalenderjahr zählt mit.

Quelle: § 23 EStG.

Probe: Kauf Dezember 2020 und Verkauf Januar 2021 ist bei Ja befreit.

## Kindergeld bis

Ja endet mit dem 25. Geburtstag. Nein endet mit 18, ohne Ausbildungs- und Einkommensprüfung.

Quelle: BKGG, Modellwahl für Nein.

Probe: Ja → 25, Nein → 18.

## Kindererziehungszeiten

Ein Erwachsener erhält die Punkte für alle Kinder zusammen (Modellwahl). Geburt ab 01.01.1992: 36 Monate, drei Entgeltpunkte. Davor: 24 Monate, zwei. Elternzeit zählt keine Entgeltpunkte.

Quelle: §§ 56 Abs. 1, 249 und 70 Abs. 2 SGB VI.

Probe: Kind 1991-12-01 und Kind 2000-06-01 → 5 Entgeltpunkte.

## Kindergeld

259 € je Kind und Monat im Jahr 2026, mit der Inflation fortgeschrieben, bis zum gewählten Endalter. Die Heirat ist keine Voraussetzung.

Quelle: BKGG, Betrag 2026.

Probe: Ein Kind, ein Monat, ohne Inflation: 259 €.

## Entnahme

Bei Erhalt bleibt der reale Wert und wächst um 0,5 % im Jahr. Bei vollem Verzehr sinkt der reale Wert bis zum Horizont auf das Restvermögen. Dazwischen mischt der Schieber beide Ziele.

Quelle: Modellwahl.

Probe: Verzehr 0 hält den realen Wert plus 0,5 % im Jahr.

## Entnahme bis zum Horizont

Bei vollem Verzehr sinkt der reale Depotwert bis zum Horizont auf das Restvermögen in Euro von heute.

Quelle: Modellwahl.

Probe: Verzehr 1 und Rest 0 senkt den realen Wert auf null am Horizont.
