#!/usr/bin/env bash
# Push main and private to a private backup remote only (never GitHub or the retired public GitLab).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RETIRED_PUBLIC_GITLAB="git@gitlab.com:meine-group4/kaufen-oder-mieten.git"

normalize_url() {
  local url="${1%/}"
  url="${url%.git}"
  url="$(printf '%s' "$url" | tr '[:upper:]' '[:lower:]')"
  printf '%s' "$url"
}

url_matches() {
  [[ "$(normalize_url "$1")" == "$(normalize_url "$2")" ]]
}

github_url=""
if git remote get-url github &>/dev/null; then
  github_url="$(git remote get-url github)"
fi

backup_url="${BUY_VS_RENT_BACKUP_REMOTE:-}"
if [[ -z "$backup_url" ]]; then
  if git remote get-url backup &>/dev/null; then
    backup_url="$(git remote get-url backup)"
  else
    echo "backup: set git remote 'backup' or BUY_VS_RENT_BACKUP_REMOTE to your private project URL." >&2
    exit 1
  fi
fi

if url_matches "$backup_url" "$RETIRED_PUBLIC_GITLAB"; then
  echo "backup: refused — backup URL is the retired public GitLab project ($backup_url)." >&2
  exit 1
fi
if [[ -n "$github_url" ]] && url_matches "$backup_url" "$github_url"; then
  echo "backup: refused — backup URL is the public GitHub remote ($github_url)." >&2
  exit 1
fi
if git remote get-url origin &>/dev/null; then
  origin_url="$(git remote get-url origin)"
  if url_matches "$backup_url" "$origin_url"; then
    echo "backup: refused — backup URL matches git remote 'origin' ($origin_url)." >&2
    exit 1
  fi
fi

git push "$backup_url" main
if git show-ref --verify --quiet refs/heads/private; then
  git push "$backup_url" private
else
  echo "backup: no local private branch; pushed main only." >&2
fi
