#!/usr/bin/env bash
# Fail if private paths are tracked on the current branch (same rule as test_git_tracks_no_plan_or_private_profile).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

tracked="$(git ls-files)"
if grep -qxF "PLAN.md" <<<"$tracked"; then
  echo "publish: PLAN.md is tracked; remove it from main before pushing to origin." >&2
  exit 1
fi
if grep -qxF "private/profile.yaml" <<<"$tracked"; then
  echo "publish: private/profile.yaml is tracked; remove it before pushing to origin." >&2
  exit 1
fi
while IFS= read -r path; do
  [[ -z "$path" ]] && continue
  if [[ "$path" != private/profile.example.yaml ]]; then
    echo "publish: unexpected tracked file under private/: $path" >&2
    exit 1
  fi
done < <(grep '^private/' <<<"$tracked" || true)
