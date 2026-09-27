# Mini PC production host

The public site is served from the home mini PC. Secrets stay on that machine under `~/.config/`; nothing below copies tokens or passwords.

## Access from the laptop

- SSH host: **`mini`** (`simon-mini@192.168.178.10`, key in laptop `~/.ssh/config`).
- Passwordless **`sudo`** on the mini is available to agents.

## Layout

| Piece | Where |
|--------|--------|
| App clone | `~/kaufen-oder-mieten` (branch `main`, GitHub HTTPS) |
| App service | `systemctl --user` unit `buy-vs-rent.service` → `buy-vs-rent serve` on **0.0.0.0:8000** (TLS via env certs) |
| Public TLS front | `systemctl --user` unit `caddy.service` → listens **:8443**, certs in `~/.config/caddy/certs/` |
| Fritz!Box | WAN **TCP 443** → `192.168.178.10:8443` |
| Port 80 | AdGuard Home (not the app) |

Wi-Fi dev URL: `https://192.168.178.10:8000`. Internet URL: `https://kauf-oder-mieten.de` (and `www`).

`BUY_VS_RENT_PROFILE` must stay **unset** on the mini so `/api/profile` is **404**.

## After `scripts/publish.sh` (engineer)

`git pull` alone is **not** enough when `pyproject.toml` version changes.

On the mini:

```bash
cd ~/kaufen-oder-mieten
git pull --ff-only origin main
.venv/bin/pip install -e ".[dev]"
systemctl --user restart buy-vs-rent.service
```

Check: `curl -fsS https://kauf-oder-mieten.de/api/version` matches the release on GitHub.

Restart **caddy** only when `deploy/caddy/Caddyfile` or cert files changed.

## DNS (Netcup CloudDNS)

- Zone is **CloudDNS only**; Caddy’s legacy Netcup DNS module does not see it.
- **A** records for apex and **www** must point at the current home WAN IPv4.
- **DynDNS token** = CloudDNS **API-Key** (CCP Stammdaten → API → API-Keys), file `~/.config/buy-vs-rent/clouddns.env`.
- On the mini: cron **`*/5`** runs `scripts/netcup-clouddns-ddns.sh` (updates **apex and www**).
- On the home LAN: `scripts/fritz-netcup-ddns.py` enables Fritz custom DynDNS for **apex on IP change** (`fritz.env` + same `clouddns.env`; `NETCUP_CUSTOMER_NUMBER` in `fritz.env`; provider password empty). See `deploy/caddy/CLOUDDNS-CERTS.md`.
- Do not probe `wsDynDns.php` with fake IPs.

Some laptops use DNS that still **NXDOMAIN** `www` while `dig @8.8.8.8` is correct; use public resolvers or mobile data to verify.

## TLS certificate

**Caddy** obtains and renews Let's Encrypt certs via **TLS-ALPN-01** on `:8443` (WAN 443 forwarded). No CloudDNS TXT for normal operation. Details: `deploy/caddy/CLOUDDNS-CERTS.md`. Manual certbot TXT remains the documented fallback.

## Config files (mini only, chmod 600)

- `~/.config/buy-vs-rent/clouddns.env` — DynDNS token
- `~/.config/buy-vs-rent/fritz.env` — Fritz API (optional; for scripts from laptop)
- `~/.config/caddy/netcup.env` — legacy Netcup API (certbot login test; not CloudDNS zone edits)
- `~/.config/caddy/certs/` — PEM for Caddy
- `~/.config/buy-vs-rent/tls/` — PEM for the app on :8000

## Google

Do not submit the site to Google while the planner hold is open.
