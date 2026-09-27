#!/usr/bin/env python3
"""Set Fritz!Box IPv4 port share: WAN EXTERNAL_PORT -> MINI_IP:INTERNAL_PORT (TCP).

Reads ~/.config/buy-vs-rent/fritz.env or FRITZBOX_* in the environment.
Requires: pip install fritzconnection (in .venv).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ENV_FILE = Path.home() / ".config" / "buy-vs-rent" / "fritz.env"
SERVICES = ("WANPPPConnection1", "WANIPConnection1")


def load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def cfg(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def connect():
    from fritzconnection import FritzConnection

    address = cfg("FRITZBOX_ADDRESS", "192.168.178.1")
    user = cfg("FRITZBOX_USER")
    password = cfg("FRITZBOX_PASSWORD")
    if not password:
        print("Missing FRITZBOX_PASSWORD (see deploy/fritz/fritz.env.example).", file=sys.stderr)
        sys.exit(1)
    return FritzConnection(address=address, user=user, password=password)


def mapping_count(fc, service: str) -> int:
    out = fc.call_action(service, "GetPortMappingNumberOfEntries")
    return int(out["NewPortMappingNumberOfEntries"])


def mapping_entry(fc, service: str, index: int) -> dict:
    return fc.call_action(
        service,
        "GetGenericPortMappingEntry",
        arguments={"NewPortMappingIndex": index},
    )


def delete_mapping(fc, service: str, entry: dict) -> None:
    fc.call_action(
        service,
        "DeletePortMapping",
        arguments={
            "NewRemoteHost": entry.get("NewRemoteHost", ""),
            "NewExternalPort": int(entry["NewExternalPort"]),
            "NewProtocol": entry["NewProtocol"],
        },
    )


def add_mapping(
    fc,
    service: str,
    *,
    external: int,
    internal: int,
    client: str,
    label: str,
) -> None:
    fc.call_action(
        service,
        "AddPortMapping",
        arguments={
            "NewRemoteHost": "",
            "NewExternalPort": external,
            "NewProtocol": "TCP",
            "NewInternalPort": internal,
            "NewInternalClient": client,
            "NewEnabled": 1,
            "NewPortMappingDescription": label,
            "NewLeaseDuration": 0,
        },
    )


def find_service(fc) -> str:
    last_auth_error: Exception | None = None
    for service in SERVICES:
        if service not in fc.services:
            continue
        try:
            mapping_count(fc, service)
            return service
        except Exception as exc:
            name = type(exc).__name__
            if "401" in str(exc) or "Authorization" in name:
                last_auth_error = exc
                break
            continue
    if last_auth_error:
        raise SystemExit(
            "Fritz!Box login failed (401). Check FRITZBOX_USER and FRITZBOX_PASSWORD in "
            f"{ENV_FILE} — use a FRITZ!Box-Benutzer with permission to change port shares, "
            "not the Wi‑Fi password."
        ) from last_auth_error
    raise SystemExit("No WANPPPConnection1/WANIPConnection1 on this Fritz!Box.")


def main() -> None:
    load_env_file(ENV_FILE)
    external = int(cfg("EXTERNAL_PORT", "443"))
    internal = int(cfg("INTERNAL_PORT", "8443"))
    client = cfg("MINI_IP", "192.168.178.10")
    label = cfg("FRITZ_RULE_LABEL", "HTTPS-Server")

    fc = connect()
    service = find_service(fc)
    print(f"Fritz: {fc.modelname}, service {service}")

    removed = 0
    count = mapping_count(fc, service)
    for index in range(count):
        entry = mapping_entry(fc, service, index)
        if int(entry["NewExternalPort"]) != external or entry["NewProtocol"] != "TCP":
            continue
        internal_port = int(entry["NewInternalPort"])
        internal_client = entry.get("NewInternalClient", "")
        if internal_port == internal and internal_client == client:
            print(f"OK: already {external} -> {client}:{internal} ({entry.get('NewPortMappingDescription', '')})")
            return
        print(f"Remove old rule: {external} -> {internal_client}:{internal_port}")
        delete_mapping(fc, service, entry)
        removed += 1
        break

    add_mapping(fc, service, external=external, internal=internal, client=client, label=label)
    print(f"Added: WAN TCP {external} -> {client}:{internal} ({label})")
    if removed:
        print("(Replaced an existing rule on the same external port.)")


if __name__ == "__main__":
    main()
