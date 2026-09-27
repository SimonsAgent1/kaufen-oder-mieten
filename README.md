# Kaufen oder mieten

Seite: https://kauf-oder-mieten.de

Eine Rechnung für ein selbst genutztes Zuhause in Deutschland: kaufen und abbezahlen, oder weiter mieten und denselben Spielraum in einem Aktien-ETF lassen.

Das Ergebnis ist keine Finanz-, Steuer- oder Kreditempfehlung. Der Sollzins startet beim Bundesbank-Durchschnitt und ist kein Angebot. Die Lohnsteuer ist eine Näherung für 2026.

Die Angaben eines Haushalts liegen in einer Szenario-Datei. Dieselbe Datei öffnet die Seite und rechnet das Terminal. Ein Beispiel ohne echte Personen liegt in [`private/profile.example.yaml`](private/profile.example.yaml).

## Installieren und die Seite öffnen

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/buy-vs-rent serve
```

Die Seite liegt unter [http://127.0.0.1:8000](http://127.0.0.1:8000). Der Chat fragt die Haushaltsdaten ab. „Beispiel ansehen“ lädt die Demodatei.

## Dieselbe Datei im Terminal

```bash
cp private/profile.example.yaml private/profile.yaml
.venv/bin/buy-vs-rent run private/profile.yaml
.venv/bin/buy-vs-rent run private/profile.yaml --json
```

`private/profile.yaml` bleibt außerhalb von Git. Die Seite exportiert dieselbe Art Datei und liest sie wieder ein, ohne sie hochzuladen. YAML und JSON sind dasselbe Schema.

Eine lokale Datei kann die Seite vorfüllen, wenn du das willst:

```bash
BUY_VS_RENT_PROFILE=private/profile.yaml .venv/bin/buy-vs-rent serve
```

Ohne diese Variable gibt es keine gespeicherten Angaben. Details stehen in [docs/privacy.md](docs/privacy.md).

## Tests

```bash
.venv/bin/pytest tests
```

## Veröffentlichen

Von einem sauberen `main` aus:

```bash
./scripts/publish.sh
```

Das Skript prüft, dass keine privaten Pfade getrackt sind, führt die Tests aus und schiebt `main` nur auf das Remote `github` (GitHub). Die Projektpfade stehen in [docs/privacy.md](docs/privacy.md). Ein privates Backup läuft nur über `scripts/backup.sh` auf das Remote `backup` (privates GitLab).

## Weiterlesen

- [docs/scenario.md](docs/scenario.md) beschreibt die Datei.
- [docs/model.md](docs/model.md) beschreibt die Rechnung.
- [docs/privacy.md](docs/privacy.md) beschreibt, was das Repository nicht enthält.
- Private Nutzung ist frei. Gewerbliche Nutzung, auch ein Makler mit Kundinnen und Kunden, braucht eine Erlaubnis. Die Lizenz ist [PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0) ([LICENSE](LICENSE)).
- `main` ist der veröffentlichte Zweig. `PLAN.md` und ein echtes Profil liegen nur auf dem lokalen Zweig `private` und nicht auf dem öffentlichen GitHub-Repository. Siehe [docs/privacy.md](docs/privacy.md).
