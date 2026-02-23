"""Simple in-process rate limiting helpers for WEMS.

Designed to fail-open safely in production if storage is unavailable.
"""

from __future__ import annotations

import time
from typing import Dict, Tuple

WINDOW_SECONDS = 3600  # rolling 1h window
LIMITS_PER_TIER = {
    "free": 60,
    "premium": 600,
    "enterprise": 5000,
}

# key => (window_start_ts, count)
_STATE: Dict[str, Tuple[float, int]] = {}


def check_rate_limit(rate_key: str, tier: str) -> dict:
    now = time.time()
    limit = LIMITS_PER_TIER.get((tier or "free").lower(), LIMITS_PER_TIER["free"])

    window_start, count = _STATE.get(rate_key, (now, 0))
    if now - window_start >= WINDOW_SECONDS:
        window_start, count = now, 0

    if count >= limit:
        return {
            "allowed": False,
            "count": count,
            "limit": limit,
            "reset_time": window_start + WINDOW_SECONDS,
        }

    count += 1
    _STATE[rate_key] = (window_start, count)
    return {
        "allowed": True,
        "count": count,
        "limit": limit,
        "reset_time": window_start + WINDOW_SECONDS,
    }


def get_limit_display(tier: str) -> str:
    t = (tier or "free").lower()
    limit = LIMITS_PER_TIER.get(t, LIMITS_PER_TIER["free"])
    return f"{t.title()} ({limit}/hour)"
