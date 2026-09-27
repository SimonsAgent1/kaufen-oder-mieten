"""German explanation page from docs/model.md."""

from __future__ import annotations

import html
import re
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _inline_md(paragraph: str) -> str:
    text = html.escape(paragraph)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = text.replace(
        "[docs/rules.md](rules.md)",
        '<a href="/regeln">Rechenregeln</a>',
    )
    return text


def render_model_html() -> str:
    raw = (_repo_root() / "docs" / "model.md").read_text(encoding="utf-8")
    lines = raw.strip().split("\n")
    title = "Rechnung"
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        body_text = "\n".join(lines[1:])
    else:
        body_text = raw
    paragraphs = []
    for block in body_text.split("\n\n"):
        block = block.strip()
        if block:
            paragraphs.append(f"<p>{_inline_md(block)}</p>")
    body_html = "\n    ".join(paragraphs)
    esc_title = html.escape(title)
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc_title}</title>
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="stylesheet" href="/static/styles.css">
</head>
<body class="legal-page">
  <header class="legal-header">
    <h1>{esc_title}</h1>
    <p><a href="/">Zurück zur Rechnung</a> · <a href="/regeln">Rechenregeln</a></p>
  </header>
  <main class="legal-body">
    {body_html}
  </main>
  <footer class="site-footer">
    <p class="site-tagline">Kostenlos, ohne Werbung, ohne Cookies.</p>
    <div class="site-footer-meta">
      <span id="app-version" class="app-version"></span>
      <a href="/">Zur Rechnung</a>
      <a href="/impressum">Impressum</a>
    </div>
    <a class="github-mark" href="https://github.com/SimonsAgent1/kaufen-oder-mieten" target="_blank" rel="noopener noreferrer" aria-label="Quelltext">
      <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
        <path fill="currentColor" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
      </svg>
    </a>
  </footer>
  <script src="/static/scenario.js"></script>
  <script>mountAppVersion();</script>
</body>
</html>"""
