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

## Topf-Auszahlung nach Wohnkosten

Auszahlung aus einem Topf minus der Lücke zwischen Wohnkosten und Einkommen, mindestens 0. Der Rest kann ins ETF.

Quelle: Modellwahl.

Probe: 10.000 € Auszahlung und 3.000 € Lücke → 7.000 € fürs ETF.

## Restschuld im Chart

Bank: Restschuld plus noch fällige Zinsen bis Tilgung oder Verkauf. Sollzins bis zur Zinsbindung, danach Anschlusszins und ggf. höhere Rate bis zur Pflege.

Quelle: Modellwahl.

Probe: 100.000 €, 3 %, 2 % Tilgung, 12 Monate ohne Wechsel: Restschuld plus Zinsen über 12 Monate.

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

Kaufpreis mal Jahresanteil, geteilt durch 12. Der Jahresanteil steht im Szenario; die Monats-Euro folgen dem Kaufpreis.

Quelle: Modellwahl.

Probe: 400.000 € mal 0,75 % im Jahr sind 250 € im Monat.

## Eigenkapitalanteil vor dem Kauf

Zusätzliches Eigenkapital als Anteil des Kaufpreises, nur wenn die Wartebedingung an ist. Nebenkosten und Einzugskosten kommen dazu.

Quelle: Modellwahl.

Probe: 400.000 € mal 15 % sind 60.000 €.

## Satz Arbeitslosengeld

60 % ohne Kind im Haushalt, 67 % mit Kind.

Quelle: § 149 SGB III.

Probe: Mit Kind → 0,67.

## Einkommen im Monat mit Jobwechsel

Jobsegmente, Arbeitslosigkeit mit Leistungsdauer, danach null bis zum nächsten Job.

Quelle: Modellwahl.

Probe: Ohne Zusatzangaben bleibt ein Gehalt mit Wachstum.

## Brutto aus Jobsegmenten

Erstes Segment ab work_start, weitere ab Jobwechsel mit eigenem Wachstum.

Quelle: Modellwahl.

Probe: Ab Jobwechsel gilt nur das neue Brutto und Wachstum.

## Arbeitslosengeld im Modell

60 % des modellierten Nettos vor dem Beginn, 67 % mit Kind im Haushalt.

Quelle: § 149 SGB III, Modellwahl.

Probe: 3.000 € Netto ohne Kind → 1.800 € im Monat.

## Dauer Arbeitslosengeld

12 Monate unter 50 Jahren, danach 15, 18 oder 24 Monate ab 50, 55 oder 58.

Quelle: § 147 SGB III, Modellwahl.

Probe: 49 Jahre → 12 Monate.

## Wachstum Altersvorsorgedepot

Der Stand wird jeden Monat mit der nominalen ETF-Rendite aus dem Schieberegler fortgeschrieben, ohne TER und ohne Vorabpauschale.

Quelle: Modellwahl.

Probe: 8,7 % im Jahr → Faktor (1,087)^(1/12) pro Monat.

## Grundzulage Altersvorsorgedepot

50 % der eigenen Beiträge bis 360 €, danach 25 % bis 1.800 €, höchstens 540 € im Jahr.

Quelle: Altersvorsorgereformgesetz, Modell 2027.

Probe: 1.200 € eigene Beiträge → 390 € Zulage.

## Kinderzulage je Kind

100 % der eigenen Beiträge, höchstens 300 € je Kind im Jahr.

Quelle: Altersvorsorgereformgesetz, Modell 2027.

Probe: 500 € eigene Beiträge → 300 € je Kind.

## Günstigerprüfung Altersvorsorgedepot

Entweder Grundzulage in den Topf oder eine Steuerersparnis aus Sonderausgaben bis 1.800 €, je nachdem was höher ist. Liegt die Ersparnis darüber, zahlt das Modell nur die Grundzulage als Erstattung und keine Zulage in den Topf.

Quelle: Altersvorsorgereformgesetz, Modell 2027.

Probe: 1.200 € eigene Beiträge → 390 € Zulage im Topf, 0 € Steuerersparnis.

## Sonderausgaben Altersvorsorgedepot

Steuerersparnis nur auf dem Sonderausgabenpfad der Günstigerprüfung.

Quelle: Altersvorsorgereformgesetz, Modell 2027.

Probe: 1.200 € eigene Beiträge → 0 € Erstattung, weil die Zulage höher ist.

## Beiträge über 1.800 €

Eigene Beiträge über 1.800 € im Jahr werden im Beitragsjahr wie eine geförderte Auszahlung besteuert.

Quelle: Altersvorsorgereformgesetz, Modell 2027.

Probe: 200 € über 1.800 € erhöhen die Steuer wie 200 € geförderte Auszahlung.

## Schenkung der Eltern

Eine Schenkung ist nicht einkommensteuerpflichtig. Der Betrag wird hälftig je Elternteil angesetzt. Je Elternteil gilt ein Freibetrag von 400.000 €. Darüber folgt Steuerklasse I nach § 19 ErbStG.

Quelle: §§ 16 Abs. 1 Nr. 2, 19 ErbStG.

Probe: 20.000 € gesamt → 0 € Steuer. 900.000 € gesamt → 7.000 € Steuer.

## Freibetrag je Elternteil

400.000 € Freibetrag je Elternteil auf die Hälfte der Schenkung.

Quelle: § 16 Abs. 1 Nr. 2 ErbStG.

Probe: 10.000 € von einem Elternteil → 0 € Steuer.

## Steuerklasse I

7 % auf die ersten 75.000 € des steuerpflichtigen Erwerbs, danach höhere Stufen nach § 19 ErbStG.

Quelle: § 19 ErbStG.

Probe: 50.000 € steuerpflichtig → 3.500 €.

## Geld von den Eltern

Schenkung netto nach Erwerbsteuer und Darlehen der Eltern erhöhen das verfügbare Bargeld im Startmonat. Das Darlehen bleibt als Schuld bis zum Ende.

Quelle: Modellwahl.

Probe: 20.000 € Schenkung → 20.000 € mehr Bargeld, 0 € Steuer.

## Noch fällige Zinsen, Darlehen der Eltern

Monatlicher Zins mal verbleibende Monate bis zum Horizont. Bei 0 % Zins ist der Betrag 0.

Quelle: Modellwahl.

Probe: 100.000 €, 3 % im Jahr, 24 Monate → 6.000 €.

## Zins auf Darlehen der Eltern

Jahresanteil der ausstehenden Schuld, in zwölf gleichen Monatszahlungen.

Quelle: Modellwahl.

Probe: 100.000 € Schuld und 3 % im Jahr → 250 € im Monat.

## Tilgung, Darlehen der Eltern

Jahresanteil der ausstehenden Schuld, in zwölf gleichen Monatszahlungen. Zins und Tilgung erscheinen im Kaufweg unter Zinsen und Tilgung.

Quelle: Modellwahl.

Probe: 100.000 € Schuld und 2 % Tilgung im Jahr → etwa 167 € im Monat.

## Miete im eigenen Haus

Kaltmiete von Mitbewohnern ist Einkünfte aus Vermietung und Verpachtung und wird mit dem persönlichen Satz besteuert, nicht als Kapitalertrag.

Quelle: § 21 EStG.

Probe: 600 € Kaltmiete im Monat erhöhen das zu versteuernde Einkommen um 7.200 € im Jahr.

## Gewinn Kapitalversicherung

Auszahlung minus eingezahlte Beiträge.

Quelle: § 20 Abs. 1 Nr. 6 EStG.

Probe: 60.000 € Auszahlung, 40.000 € Beiträge → 20.000 € Gewinn.

## Steuer Kapital- oder Einmalrente

Mindestens zwölf Jahre und Auszahlung ab 62: halber Gewinn mit persönlichem Satz. Sonst 25 % plus Soli auf den ganzen Gewinn.

Quelle: § 20 Abs. 1 Nr. 6 EStG.

Probe: 20.000 € Gewinn unter zwölf Jahren → 25 % plus Soli.

## Ertragsanteil private Leibrente

Ab 67 Jahren sind 17 % der Jahresrente steuerpflichtig.

Quelle: § 22 Nr. 1 EStG.

Probe: 12.000 € im Jahr → 2.040 € steuerpflichtig.

## Steuer private Leibrente

Der Ertragsanteil erhöht das zu versteuernde Einkommen; die zusätzliche Einkommensteuer plus Soli wird berechnet.

Quelle: § 22 Nr. 1 EStG.

Probe: 2.040 € Ertragsanteil erhöht die Steuerlast.

## Steuer geförderter Auszahlung

Die Auszahlung aus Riester oder Altersvorsorgedepot ist voll steuerpflichtig.

Quelle: § 22 Nr. 5 EStG.

Probe: 20.000 € Auszahlung erhöhen das zu versteuernde Einkommen um 20.000 €.

## Rückkaufswerte der Töpfe

Summe der eingetragenen Rückkaufswerte aktiver Töpfe bis zur Auszahlung.

Quelle: Modellwahl.

Probe: Zwei Töpfe mit 10.000 € und 5.000 € → 15.000 €.

## Kinderzulage gesamt

Kinderzulage je Kind mal Anzahl der Kinder unter 25 im Modell.

Quelle: Altersvorsorgereformgesetz, Modell 2027.

Probe: 300 € je Kind, zwei Kinder → 600 €.

## Vergleichsmiete im Monat

Vergleichskaltmiete in Euro von heute, einmal im Jahr mit der Mietsteigerung fortgeschrieben. Sie dient dem Kaufpreisfaktor, nicht dem Monatschart.

Quelle: Modellwahl.

Probe: 1.200 € Kaltmiete und 0 % Mietsteigerung → 1.200 € im Monat.

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
