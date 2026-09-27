# Für Agenten

Die verbindlichen Regeln liegen in `.cursor/rules/`. Wenn eine Änderung eine Regel falsch macht, wird die Regel in derselben Änderung mitgezogen.

Die Rechnung, die Formeln und die Datei sind in `docs/model.md`, `docs/rules.md` und `docs/scenario.md` beschrieben. Was nicht ins Git gehört, steht in `docs/privacy.md`.

Tests: `.venv/bin/pytest tests` nach `pip install -e ".[dev]"`.
