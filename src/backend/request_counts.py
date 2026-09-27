"""Daily request totals on disk. No IP, no cookie, no person id."""

from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

Berlin = ZoneInfo("Europe/Berlin")

DayTotals = dict[str, int]
Store = dict[str, DayTotals]

_KEYS = ("page", "compare_ok", "compare_reject")


def counts_path() -> Path:
    raw = os.environ.get("BUY_VS_RENT_COUNTS_FILE")
    if raw:
        return Path(raw)
    return Path.home() / ".local/state/buy-vs-rent/daily-counts.json"


def today_key(when: datetime | None = None) -> str:
    moment = when or datetime.now(Berlin)
    return moment.astimezone(Berlin).date().isoformat()


def _empty_day() -> DayTotals:
    return {key: 0 for key in _KEYS}


def _load() -> Store:
    path = counts_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(data, dict):
        return {}
    out: Store = {}
    for day, row in data.items():
        if not isinstance(day, str) or not isinstance(row, dict):
            continue
        out[day] = _empty_day()
        for key in _KEYS:
            val = row.get(key, 0)
            if isinstance(val, int) and val >= 0:
                out[day][key] = val
    return out


def _save(store: Store) -> None:
    path = counts_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _bump(field: str, when: datetime | None = None) -> None:
    store = _load()
    day = today_key(when)
    row = store.setdefault(day, _empty_day())
    row[field] = row.get(field, 0) + 1
    _save(store)


def record_page_load(when: datetime | None = None) -> None:
    _bump("page", when)


def record_compare_ok(when: datetime | None = None) -> None:
    _bump("compare_ok", when)


def record_compare_reject(when: datetime | None = None) -> None:
    _bump("compare_reject", when)


def recent_days(last: int = 30, anchor: date | None = None) -> list[tuple[str, DayTotals]]:
    end = anchor or datetime.now(Berlin).date()
    store = _load()
    rows: list[tuple[str, DayTotals]] = []
    for offset in range(last):
        day = (end - timedelta(days=offset)).isoformat()
        rows.append((day, store.get(day, _empty_day())))
    return rows


PUBLIC_HOST_SUFFIXES = (".kauf-oder-mieten.de",)
PUBLIC_HOSTS = frozenset({"kauf-oder-mieten.de", "www.kauf-oder-mieten.de"})

PUBLIC_SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
}


def _effective_host(host_header: str | None, forwarded_host: str | None = None) -> str:
    effective = forwarded_host or host_header
    if not effective:
        return ""
    return effective.split(",")[0].split(":")[0].strip().lower().rstrip(".")


def public_site_host(host_header: str | None, forwarded_host: str | None = None) -> bool:
    """True for kauf-oder-mieten.de and www on the public internet, not the home LAN host."""
    host = _effective_host(host_header, forwarded_host)
    if not host:
        return False
    if host in PUBLIC_HOSTS:
        return True
    return any(host.endswith(suffix) for suffix in PUBLIC_HOST_SUFFIXES)


def render_zahlen_html(frontend_dir: Path) -> str:
    rows = []
    for day, totals in recent_days():
        rows.append(
            "<tr>"
            f"<td>{day}</td>"
            f"<td>{totals['page']}</td>"
            f"<td>{totals['compare_ok']}</td>"
            f"<td>{totals['compare_reject']}</td>"
            "</tr>"
        )
    template = (frontend_dir / "zahlen.html").read_text(encoding="utf-8")
    return template.replace("<!--ROWS-->", "\n        ".join(rows) if rows else "")


def zahlen_allowed(host_header: str | None, forwarded_host: str | None = None) -> bool:
    """True only for the home/LAN host name the browser asked for, not the public site."""
    host = _effective_host(host_header, forwarded_host)
    if not host:
        return False
    if host in PUBLIC_HOSTS:
        return False
    if any(host.endswith(suffix) for suffix in PUBLIC_HOST_SUFFIXES):
        return False
    if host in {"localhost", "127.0.0.1", "::1"}:
        return True
    if host.startswith("192.168.") or host.startswith("10.") or host.startswith("172."):
        return True
    if host == "simon-mini":
        return True
    return False
