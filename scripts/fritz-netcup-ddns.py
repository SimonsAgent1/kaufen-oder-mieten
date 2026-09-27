#!/usr/bin/env python3
"""Enable Fritz!Box custom DynDNS URL for Netcup CloudDNS (apex). Token from clouddns.env."""
from __future__ import annotations

import os
import sys
from pathlib import Path

FRITZ_ENV = Path.home() / ".config/buy-vs-rent/fritz.env"
CLOUD_ENV = Path.home() / ".config/buy-vs-rent/clouddns.env"


def load_env(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> None:
    load_env(FRITZ_ENV)
    load_env(CLOUD_ENV)
    token = os.environ.get("NETCUP_CLOUDDNS_TOKEN")
    if not token:
        print(f"Missing NETCUP_CLOUDDNS_TOKEN in {CLOUD_ENV}", file=sys.stderr)
        sys.exit(1)
    customer = os.environ.get("NETCUP_CUSTOMER_NUMBER") or os.environ.get(
        "FRITZBOX_CUSTOMER_NUMBER", ""
    )
    fritz_password = os.environ.get("FRITZBOX_PASSWORD", "")
    user = os.environ.get("FRITZBOX_USER", "")
    if not fritz_password:
        print("Missing FRITZBOX_PASSWORD in fritz.env", file=sys.stderr)
        sys.exit(1)
    # Netcup wsDynDns uses token= in the URL; Fritz provider fields are customer + empty password.
    ddns_password = os.environ.get("NETCUP_DDNS_PASSWORD", "")

    from fritzconnection import FritzConnection

    fc = FritzConnection(
        address=os.environ.get("FRITZBOX_ADDRESS", "192.168.178.1"),
        user=user,
        password=fritz_password,
    )
    # Fritz replaces <ipaddr> with the current WAN IPv4.
    update_url = (
        "https://customercontrolpanel.de/wsDynDns.php?action=update"
        f"&token={token}&fqdn=kauf-oder-mieten.de&ipv4Address=<ipaddr>"
    )
    fc.call_action(
        "X_AVM-DE_RemoteAccess1",
        "SetDDNSConfig",
        arguments={
            "NewEnabled": 1,
            "NewProviderName": "Benutzerdefiniert",
            "NewUpdateURL": update_url,
            "NewDomain": "kauf-oder-mieten.de",
            "NewUsername": customer,
            "NewPassword": ddns_password,
            "NewMode": "ddns_v4",
            "NewServerIPv4": "",
            "NewServerIPv6": "",
        },
    )
    info = fc.call_action("X_AVM-DE_RemoteAccess1", "GetDDNSInfo")
    print("DynDNS enabled:", info.get("NewEnabled"), "domain:", info.get("NewDomain"))


if __name__ == "__main__":
    main()
