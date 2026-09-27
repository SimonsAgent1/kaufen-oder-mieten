# TLS with Netcup CloudDNS

Public HTTPS terminates on **Caddy** on the mini (LAN **8443**, Fritz WAN **443** → **8443**). Port **80** stays AdGuard Home.

## Automatic certificates (TLS-ALPN-01)

Caddy obtains and renews Let's Encrypt certs without DNS TXT. The ACME validator connects to **port 443** on your WAN IP; the Fritz!Box forwards to Caddy on **8443**. The site block uses `alt_tlsalpn_port 8443` and disables the HTTP challenge (port 80 is not the app).

Config: `deploy/caddy/Caddyfile` on the mini at `~/.config/caddy/Caddyfile`.

```bash
scp deploy/caddy/Caddyfile mini:.config/caddy/Caddyfile
ssh mini '~/bin/caddy validate --config ~/.config/caddy/Caddyfile --adapter caddyfile && systemctl --user restart caddy.service'
```

Certs are stored in Caddy’s data directory (typically under `~/.local/share/caddy/`). After a config change, check:

```bash
ssh mini 'journalctl --user -u caddy.service -n 30 --no-pager'
curl -fsSI https://kauf-oder-mieten.de/ | grep -i expire
```

## Fallback: manual certbot + DNS TXT

Use this only if TLS-ALPN renewal fails (firewall, Fritz rule, or Caddy down during renew).

Caddy’s Netcup DNS module uses the **legacy** DNS API. CloudDNS-only zones cannot use it (`5029`). `scripts/netcup-txt-probe.py` could not log in to the JSON DNS API (4013) with keys on the mini.

Manual issue with certbot, TXT in the CloudDNS UI, then point Caddy at files under `~/.config/caddy/certs/` (see git history of `Caddyfile` before TLS-ALPN).

## DynDNS (A records when the home IP changes)

CloudDNS has no separate DynDNS token in the zone UI. Use an **API-Key** from CCP **Stammdaten → API → API-Keys** as `NETCUP_CLOUDDNS_TOKEN` (see `clouddns.env.example`). Official update URL: [Dynamic DNS](https://www.netcup.com/de/helpcenter/dokumentation/domain/dyn-dns).

On the mini:

```bash
cp deploy/caddy/clouddns.env.example ~/.config/buy-vs-rent/clouddns.env
chmod 600 ~/.config/buy-vs-rent/clouddns.env
./scripts/netcup-clouddns-ddns.sh
```

**Fritz (on IP change):** `scripts/fritz-netcup-ddns.py` from the home LAN with `fritz.env` and `clouddns.env`.

**Cron (apex + www):** `*/5 * * * *` … `netcup-clouddns-ddns.sh` (see `deploy/mini-pc.md`).

Do not probe `wsDynDns.php` with fake IPs.
