#!/usr/bin/env bash
# Bump pyproject patch for a publish, unless HEAD is already the release commit.
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

ver="$(package_version)"
release_msg="chore: release ${ver}"

if [[ "$(git log -1 --format=%s 2>/dev/null || true)" == "${release_msg}" ]]; then
  exit 0
fi

new_ver="$(bump_patch "$ver")"
sed -i "s/^version = \".*\"/version = \"${new_ver}\"/" "$PYPROJECT"
git add "$PYPROJECT"
git commit -m "chore: release ${new_ver}"
