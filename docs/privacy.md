# Datenschutz im Repository

Auf `main` liegt der öffentliche Code. Der Zweig `private` bleibt lokal: dort dürfen `PLAN.md` und `private/profile.yaml` liegen. `private` wird nicht nach `main` gemergt und nicht auf das öffentliche Remote geschoben.

Veröffentlicht wird nur über `scripts/publish.sh` (Prüfung, Tests, Patch-Version in `pyproject.toml` als Commit `chore: release`, dann `git push github main`). Schlägt der Push fehl und `HEAD` ist schon der Release-Commit, wird beim erneuten Lauf nicht noch einmal hochgezählt. Das öffentliche Git-Remote ist GitHub: `SimonsAgent1/kaufen-oder-mieten` (`github`). Der Zweig `private` wird nie auf dieses Remote geschoben.

Auf `main` läuft die Prüfung in GitHub Actions: `pytest` und dieselbe Leak-Prüfung wie lokal, ohne `BUY_VS_RENT_PROFILE` und ohne den Zweig `private`.

Das private Backup-Remote `backup` nimmt nur `scripts/backup.sh` (`main` und `private`). Dieselbe URL wie `github` lehnt das Skript ab.

Eingecheckt wird nur `private/profile.example.yaml`. Das ist die Demodatei für die Seite, das Terminal und die README.

Nicht einchecken: `PLAN.md`, `private/profile.yaml` und `private/*.local.yaml`. Sie stehen in `.gitignore`. Ein Test bricht ab, wenn `git ls-files` sie trotzdem listet.

Die Seite liest eine lokale Datei nur, wenn `BUY_VS_RENT_PROFILE` auf sie zeigt. Ohne die Variable antwortet `/api/profile` mit 404. Ein öffentlicher Start setzt die Variable nicht. Es gibt keinen Speicher für Szenarien auf dem Server.

Im Browser liegt eine Liste von Szenarien unter `buy-vs-rent-scenarios` in `localStorage`. Jede Zeile hat eine eigene id und zeigt nur die Namen der Erwachsenen. Beim ersten Laden nach dem Update wird ein alter Einzel-Schlüssel einmal in die Liste übernommen und dann gelöscht. Wenn der Server mit `BUY_VS_RENT_PROFILE` startet, wird diese Datei einmal in die Liste kopiert; die Zeile hat dasselbe Label und denselben Entfernen-Button wie andere Zeilen. Entfernen löscht nur die Zeile im Browser, nicht die Datei auf der Festplatte. „Zurücksetzen“ geht zurück zur Auswahl; andere Zeilen bleiben. Eine Zeile kann auf der Auswahl entfernt werden. „Rechnen“ aktualisiert die geöffnete Zeile; „Neu anfangen“ legt beim ersten „Rechnen“ eine neue Zeile an. Das Beispiel wird nicht in der Liste gespeichert.

Export lädt die Datei herunter und sagt, dass Einkommen und Geburtsdaten darin stehen. Import fügt eine Zeile hinzu und bleibt auf der Auswahl. Import liest eine Datei nur im Browser und lädt sie nicht hoch.

Ein Link `?wohnung=` darf nur den Kaufblock für ein Haus oder eine Wohnung tragen: Preis, Bundesland, Notar, Makler, Eigentümerkosten. Keine Einzugskosten und kein Gehalt. Alles andere wird verworfen.

Die Demodatei ist keine echte Haushaltsgeschichte. „Beispiel ansehen“ zeigt das an.

## Datenschutz auf der Seite

Der Text im Seitenkopf ist die Datenschutzerklärung für den Betrieb unter `kauf-oder-mieten.de`. Verantwortlicher ist Simon Muchau, erreichbar unter `simon.muchau@freenet.de`. Die Seite ist privat und nicht geschäftlich; es gibt kein Impressum.

Haushaltsangaben bleiben im Browser (`localStorage`). Export ist ein Download; Import liest nur lokal. Ein `?wohnung=`-Link trägt kein Einkommen und kein Geburtsdatum.

„Rechnen“ sendet das Szenario einmal an den Server für die Antwort. Der Server speichert es nicht. Pro Aufruf von `/api/compare` schreibt das Programm höchstens eine Logzeile mit Status und Client-Adresse, ohne Szenario-Inhalt, ohne Gehalt, ohne Geburtsdatum und ohne Namen.

Der Schalter Kirchensteuer betrifft Religionszugehörigkeit (Art. 9 DSGVO). Die Seite fragt zuerst eine ausdrückliche Einwilligung ab; ohne sie bleibt `church_tax` aus und wird nicht an den Server geschickt.

Beim Aufruf sehen Betreiber-Infrastruktur (Mini-PC, Fritz!Box) die Verbindung, insbesondere die IP-Adresse. Die Entwicklungsseite im heimischen WLAN (`http://192.168.178.10:8000`) läuft ohne TLS. Geplant ist HTTPS auf `kauf-oder-mieten.de`; dann ist der Seitenname sichtbar, nicht der Inhalt des Formulars. Es werden keine Schriftarten oder Skripte von Drittanbietern geladen. Eine feste Löschfrist für Verbindungslogs ist nicht festgelegt; Anfragen an die genannte Adresse gelten dem Log, falls vorhanden, und der Kopie im Browser.
