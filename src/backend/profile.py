"""Optional local scenario. A public server leaves the environment variable unset."""

from __future__ import annotations

import os
from pathlib import Path

from buy_vs_rent.scenario import Scenario, load_scenario

PROFILE_ENV = "BUY_VS_RENT_PROFILE"


def load_profile() -> Scenario | None:
    raw = os.environ.get(PROFILE_ENV)
    if not raw:
        return None
    return load_scenario(Path(raw))
