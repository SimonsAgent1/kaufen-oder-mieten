#!/usr/bin/env bash
# Pull GitHub main on the home mini PC, reinstall the package, restart HTTPS serve.
set -euo pipefail

ssh mini 'cd ~/kaufen-oder-mieten && git fetch origin main && git reset --hard origin/main && .venv/bin/pip install -q -e ".[dev]" && systemctl --user restart buy-vs-rent.service'
