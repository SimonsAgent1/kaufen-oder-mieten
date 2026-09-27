# TLS with Netcup CloudDNS

Caddy’s Netcup DNS module uses the **Legacy DNS API**. If the domain only has a **CloudDNS** tab in CCP, that API cannot see your zone (`5029` / zone not found). Use **certbot** with a **manual** DNS challenge and TXT records in the CloudDNS UI.

Certs live under `~/.config/caddy/certs/` on the mini (no `/etc/letsencrypt` required).

## One-time issue (on the mini)

```bash
mkdir -p ~/.config/caddy/certs
sudo apt install -y certbot   # if needed

certbot certonly --manual --preferred-challenges dns \
  --config-dir ~/.config/letsencrypt \
  --work-dir ~/.config/letsencrypt-work \
  --logs-dir ~/.config/letsencrypt-logs \
  -d kauf-oder-mieten.de -d www.kauf-oder-mieten.de \
  --agree-tos -m simon.muchau@freenet.de
```

Certbot prints one or more **TXT** challenges. For each:

1. CCP → domain → **CloudDNS** → add **TXT** with the exact name and value Certbot shows.
2. Wait 2–5 minutes. Check: `dig +short TXT _acme-challenge.kauf-oder-mieten.de @8.8.8.8`
3. Press Enter in Certbot only when the TXT is visible.

Then install certs for Caddy:

```bash
cp ~/.config/letsencrypt/live/kauf-oder-mieten.de/fullchain.pem ~/.config/caddy/certs/fullchain.pem
cp ~/.config/letsencrypt/live/kauf-oder-mieten.de/privkey.pem ~/.config/caddy/certs/privkey.pem
chmod 600 ~/.config/caddy/certs/privkey.pem
systemctl --user restart caddy.service
```

Pull the repo Caddyfile (or copy `deploy/caddy/Caddyfile`) to `~/.config/caddy/Caddyfile` before restart.

## Renewal (~every 90 days)

```bash
certbot renew --manual --preferred-challenges dns \
  --config-dir ~/.config/letsencrypt \
  --work-dir ~/.config/letsencrypt-work \
  --logs-dir ~/.config/letsencrypt-logs
```

Repeat TXT steps in CloudDNS, then copy `fullchain.pem` / `privkey.pem` again and `systemctl --user restart caddy.service`.

When Netcup documents a CloudDNS API for arbitrary TXT records, we can automate this again.
