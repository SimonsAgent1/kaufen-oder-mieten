#!/usr/bin/env bash
# Bump pyproject for a publish, unless HEAD is already the release commit.
# BUY_VS_RENT_RELEASE_BUMP: patch (default) or minor (last segment set to 0).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYPROJECT="$ROOT/pyproject.toml"

package_version() {
  sed -nE 's/^version = "([^"]+)".*/\1/p' "$PYPROJECT"
}

bump_patch() {
  local v="$1"
  local major minor patch
  IFS=. read -r major minor patch <<< "$v"
  echo "${major}.${minor}.$((patch + 1))"
}

bump_minor() {
  local v="$1"
  local major minor patch
  IFS=. read -r major minor patch <<< "$v"
  echo "${major}.$((minor + 1)).0"
}

ver="$(package_version)"
release_msg="chore: release ${ver}"

if [[ "$(git log -1 --format=%s 2>/dev/null || true)" == "${release_msg}" ]]; then
  exit 0
fi

kind="${BUY_VS_RENT_RELEASE_BUMP:-patch}"
case "$kind" in
  patch) new_ver="$(bump_patch "$ver")" ;;
  minor) new_ver="$(bump_minor "$ver")" ;;
  *)
    echo "release-version: unknown BUY_VS_RENT_RELEASE_BUMP=${kind} (use patch or minor)." >&2
    exit 1
    ;;
esac

sed -i "s/^version = \".*\"/version = \"${new_ver}\"/" "$PYPROJECT"
git add "$PYPROJECT"
git commit -m "chore: release ${new_ver}"
