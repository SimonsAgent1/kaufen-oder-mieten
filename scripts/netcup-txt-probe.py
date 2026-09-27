#!/usr/bin/env python3
"""Probe Netcup DNS API: can we add and remove a harmless ACME-style TXT on CloudDNS?

Reads ~/.config/caddy/netcup.env (legacy) and ~/.config/buy-vs-rent/clouddns.env.
Prints status codes only; never prints secrets.
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://ccp.netcup.net/run/webservice/servers/endpoint.php?JSON"
DOMAIN = "kauf-oder-mieten.de"
HOST = "_acme-challenge-engineer-probe"
TXT = "buy-vs-rent-txt-probe"


def load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        out[key.strip()] = value.strip()
    return out


def post(payload: dict) -> dict:
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def login_attempt(customer: str, apikey: str, apipassword: str) -> tuple[str | None, dict]:
    data = post(
        {
            "action": "login",
            "param": {
                "customernumber": customer,
                "apikey": apikey,
                "apipassword": apipassword,
            },
        }
    )
    if data.get("status") == "success" and data.get("statuscode") == 2000:
        sid = (data.get("responsedata") or {}).get("apisessionid")
        return sid, data
    return None, data


def main() -> None:
    legacy = load_env(Path.home() / ".config/caddy/netcup.env")
    cloud = load_env(Path.home() / ".config/buy-vs-rent/clouddns.env")
    customer = legacy.get("NETCUP_CUSTOMER_NUMBER", "")
    token = cloud.get("NETCUP_CLOUDDNS_TOKEN") or legacy.get("NETCUP_API_KEY", "")

    attempts: list[tuple[str, str, str]] = []
    if legacy.get("NETCUP_API_KEY") and legacy.get("NETCUP_API_PASSWORD"):
        attempts.append(("legacy", legacy["NETCUP_API_KEY"], legacy["NETCUP_API_PASSWORD"]))
    if token:
        attempts.append(("clouddns-key-empty-pass", token, ""))
        if legacy.get("NETCUP_API_PASSWORD"):
            attempts.append(("clouddns-key-legacy-pass", token, legacy["NETCUP_API_PASSWORD"]))

    session: str | None = None
    used = ""
    for name, key, pw in attempts:
        session, resp = login_attempt(customer, key, pw)
        print(f"login:{name}", resp.get("status"), resp.get("statuscode"), resp.get("shortmessage"))
        if session:
            used = name
            break

    if not session:
        print("RESULT: no_api_login")
        sys.exit(2)

    zone = post(
        {
            "action": "infoDnsZone",
            "param": {
                "customernumber": customer,
                "apikey": attempts[[a[0] for a in attempts].index(used)][1],
                "apisessionid": session,
                "domainname": DOMAIN,
            },
        }
    )
    print("infoDnsZone", zone.get("status"), zone.get("statuscode"), zone.get("shortmessage"))

    apikey = attempts[[a[0] for a in attempts].index(used)][1]
    add = post(
        {
            "action": "updateDnsRecords",
            "param": {
                "customernumber": customer,
                "apikey": apikey,
                "apisessionid": session,
                "domainname": DOMAIN,
                "dnsrecordset": {
                    "dnsrecords": [
                        {
                            "hostname": HOST,
                            "type": "TXT",
                            "destination": TXT,
                            "deleterecord": False,
                        }
                    ]
                },
            },
        }
    )
    print("add_txt", add.get("status"), add.get("statuscode"), add.get("shortmessage"))

    if add.get("status") != "success":
        post(
            {
                "action": "logout",
                "param": {
                    "customernumber": customer,
                    "apikey": apikey,
                    "apisessionid": session,
                },
            }
        )
        print("RESULT: txt_write_failed")
        sys.exit(3)

    delete = post(
        {
            "action": "updateDnsRecords",
            "param": {
                "customernumber": customer,
                "apikey": apikey,
                "apisessionid": session,
                "domainname": DOMAIN,
                "dnsrecordset": {
                    "dnsrecords": [
                        {
                            "hostname": HOST,
                            "type": "TXT",
                            "destination": TXT,
                            "deleterecord": True,
                        }
                    ]
                },
            },
        }
    )
    print("delete_txt", delete.get("status"), delete.get("statuscode"), delete.get("shortmessage"))
    post(
        {
            "action": "logout",
            "param": {
                "customernumber": customer,
                "apikey": apikey,
                "apisessionid": session,
            },
        }
    )
    if delete.get("status") == "success":
        print("RESULT: txt_write_delete_ok")
        sys.exit(0)
    print("RESULT: txt_delete_failed")
    sys.exit(4)


if __name__ == "__main__":
    main()
