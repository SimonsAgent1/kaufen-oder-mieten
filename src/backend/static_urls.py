"""Cache-bust frontend static assets with the installed package version."""

from __future__ import annotations

import re
from importlib.metadata import version
from pathlib import Path

_STATIC_REF = re.compile(r'(href|src)="/static/([^"]+)"')


def app_release_version() -> str:
    return version("buy-vs-rent")


def with_versioned_static_urls(html: str, ver: str | None = None) -> str:
    release = ver or app_release_version()

    def repl(match: re.Match[str]) -> str:
        attr, path = match.group(1), match.group(2)
        if "?" in path:
            return match.group(0)
        return f'{attr}="/static/{path}?v={release}"'

    return _STATIC_REF.sub(repl, html)


def read_versioned_html(path: Path, ver: str | None = None) -> str:
    return with_versioned_static_urls(path.read_text(encoding="utf-8"), ver)
