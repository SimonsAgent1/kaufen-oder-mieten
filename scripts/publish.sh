#!/usr/bin/env bash
# Only supported push of main to the public GitHub remote.
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

refuse_retired_public_gitlab() {
  local url="$1"
  local label="$2"
  if url_matches "$url" "$RETIRED_PUBLIC_GITLAB"; then
    echo "publish: refused — retired public GitLab remote ($label: $url)." >&2
    exit 1
  fi
}

if [[ "$(git branch --show-current)" != main ]]; then
  echo "publish: checkout main first." >&2
  exit 1
fi

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "publish: commit or stash local changes first." >&2
  exit 1
fi

"$ROOT/scripts/git-leak-check.sh"

cp private/profile.example.yaml src/backend/profile.example.yaml

if [[ ! -x "$ROOT/.venv/bin/pytest" ]]; then
  echo "publish: missing .venv/bin/pytest; run pip install -e \".[dev]\"." >&2
  exit 1
fi

"$ROOT/.venv/bin/pytest" tests -q

"$ROOT/scripts/release-version.sh"

if [[ "${BUY_VS_RENT_PUBLISH_SKIP_PUSH:-}" == 1 ]]; then
  exit 0
fi

if ! git remote get-url github &>/dev/null; then
  echo "publish: missing git remote 'github' (public GitHub)." >&2
  exit 1
fi

github_url="$(git remote get-url github)"
refuse_retired_public_gitlab "$github_url" "github"

while IFS= read -r name; do
  [[ -z "$name" ]] && continue
  refuse_retired_public_gitlab "$(git remote get-url "$name")" "$name"
done < <(git remote)

git push github main
