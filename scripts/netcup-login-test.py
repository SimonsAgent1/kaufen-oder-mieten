#!/usr/bin/env python3
"""One Netcup DNS API login attempt. Reads ~/.config/caddy/netcup.env on the host you run it on."""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path.home() / ".config/caddy/netcup.env"
URL = "https://ccp.netcup.net/run/webservice/servers/endpoint.php?JSON"


def main() -> None:
    if not ENV.is_file():
        print(f"Missing {ENV}", file=sys.stderr)
        sys.exit(1)
    env: dict[str, str] = {}
    for line in ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip()
    for key in ("NETCUP_CUSTOMER_NUMBER", "NETCUP_API_KEY", "NETCUP_API_PASSWORD"):
        if key not in env or not env[key]:
            print(f"Missing or empty {key} in {ENV}", file=sys.stderr)
            sys.exit(1)
    if not re.fullmatch(r"\d+", env["NETCUP_CUSTOMER_NUMBER"]):
        print("NETCUP_CUSTOMER_NUMBER must be digits only (Kundennummer from CCP).", file=sys.stderr)
        sys.exit(1)
    payload = {
        "action": "login",
        "param": {
            "customernumber": env["NETCUP_CUSTOMER_NUMBER"],
            "apikey": env["NETCUP_API_KEY"],
            "apipassword": env["NETCUP_API_PASSWORD"],
        },
    }
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"HTTP {exc.code}", file=sys.stderr)
        sys.exit(1)
    code = data.get("statuscode")
    print(data.get("status"), code, "-", data.get("shortmessage"))
    if data.get("longmessage"):
        print(data.get("longmessage"))
    if data.get("status") == "success" and code == 2000:
        print("Login OK. Caddy DNS challenge can use this key.")
        sys.exit(0)
    if code == 4013 and "180 requests" in (data.get("longmessage") or ""):
        print(
            "\nNetcup often returns this text for wrong API data, not only for rate limits.\n"
            "In CCP: new DNS API key, copy all three values once, update netcup.env, wait 10 minutes,\n"
            "then run this script again (only once). Check CCP → API → log for login lines.",
            file=sys.stderr,
        )
    sys.exit(1)


if __name__ == "__main__":
    main()
