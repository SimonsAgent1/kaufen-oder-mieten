#!/usr/bin/env bash
# Install or refresh Caddy (Netcup DNS module) on the home mini PC. Secrets stay on the mini only.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CADDY_URL='https://caddyserver.com/api/download?os=linux&arch=amd64&p=github.com%2Fcaddy-dns%2Fnetcup'

ssh mini bash -s <<REMOTE
set -euo pipefail
CADDY_URL='$CADDY_URL'
mkdir -p ~/bin ~/.config/caddy ~/.config/systemd/user
if [[ ! -f ~/.config/caddy/netcup.env ]]; then
  echo "mini-caddy: missing ~/.config/caddy/netcup.env (see deploy/caddy/netcup.env.example)" >&2
  exit 1
fi
chmod 600 ~/.config/caddy/netcup.env
curl -fsSL "\$CADDY_URL" -o ~/bin/caddy.new
chmod +x ~/bin/caddy.new
mv ~/bin/caddy.new ~/bin/caddy
~/bin/caddy version
loginctl enable-linger "$USER" >/dev/null 2>&1 || true
REMOTE

scp "$ROOT/deploy/caddy/Caddyfile" mini:.config/caddy/Caddyfile
scp "$ROOT/deploy/caddy/caddy.service" mini:.config/systemd/user/caddy.service

ssh mini 'systemctl --user daemon-reload && systemctl --user enable caddy.service && systemctl --user restart caddy.service && sleep 2 && systemctl --user status caddy.service --no-pager | head -15'
