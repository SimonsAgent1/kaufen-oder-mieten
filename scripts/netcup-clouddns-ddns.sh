#!/usr/bin/env bash
# Update CloudDNS A records for apex and www to this host's public IPv4 (DynDNS API).
set -euo pipefail

ENV_FILE="${HOME}/.config/buy-vs-rent/clouddns.env"
API="https://customercontrolpanel.de/wsDynDns.php"

if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  set -a && source "$ENV_FILE" && set +a
fi

if [[ -z "${NETCUP_CLOUDDNS_TOKEN:-}" ]]; then
  echo "Missing NETCUP_CLOUDDNS_TOKEN in $ENV_FILE (see deploy/caddy/clouddns.env.example)" >&2
  exit 1
fi

IPV4="$(curl -4 -fsS --max-time 15 ifconfig.me)"
echo "Public IPv4: $IPV4"

for FQDN in kauf-oder-mieten.de www.kauf-oder-mieten.de; do
  URL="${API}?action=update&token=${NETCUP_CLOUDDNS_TOKEN}&fqdn=${FQDN}&ipv4Address=${IPV4}"
  RESP="$(curl -fsS --max-time 30 "$URL")"
  echo "$FQDN: $RESP"
done
