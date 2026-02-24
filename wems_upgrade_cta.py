"""Contextual upgrade CTA helpers with in-process cooldowns.

Fail-open by design: if CTA logic fails, request handling should continue.
"""

from __future__ import annotations

import os
import time
from typing import Dict, Optional


CTA_COOLDOWN_MINUTES = int(os.environ.get("WEMS_CTA_COOLDOWN_MINUTES", "60"))
CTA_THRESHOLDS = (0.70, 0.85, 1.00)

# key: {rate_key}:{trigger} -> last_shown_epoch
_CTA_STATE: Dict[str, float] = {}


def _should_emit(rate_key: str, trigger: str, now: Optional[float] = None) -> bool:
    now = time.time() if now is None else now
    key = f"{rate_key}:{trigger}"
    last = _CTA_STATE.get(key)
    if last is not None and (now - last) < CTA_COOLDOWN_MINUTES * 60:
        return False
    _CTA_STATE[key] = now
    return True


def threshold_trigger(count: int, limit: int) -> Optional[str]:
    """Return threshold trigger id when usage crosses 70/85/100% marks."""
    if limit <= 0:
        return None
    ratio = count / float(limit)
    if ratio >= CTA_THRESHOLDS[2]:
        return "threshold_100"
    if ratio >= CTA_THRESHOLDS[1]:
        return "threshold_85"
    if ratio >= CTA_THRESHOLDS[0]:
        return "threshold_70"
    return None


def build_upgrade_cta(*, trigger: str, rate_key: str = "anonymous", feature: Optional[str] = None) -> str:
    """Build a contextual CTA message. Returns empty string if cooldown suppresses it."""
    if not _should_emit(rate_key=rate_key, trigger=trigger):
        return ""

    if trigger == "rate_limit_exceeded":
        headline = "You hit your hourly limit on Free tier."
    elif trigger == "premium_feature_attempt":
        headline = f"{feature or 'This feature'} requires WEMS Premium."
    elif trigger == "threshold_70":
        headline = "You’ve used 70% of your hourly Free-tier quota."
    elif trigger == "threshold_85":
        headline = "You’ve used 85% of your hourly Free-tier quota."
    elif trigger == "threshold_100":
        headline = "You’ve used 100% of your hourly Free-tier quota."
    else:
        headline = "Upgrade to WEMS Premium for higher limits and advanced monitoring."

    return (
        f"\n\n─── 🔒 ───\n"
        f"{headline}\n"
        f"Premium unlocks higher throughput, full history, all regions, and advanced alert controls.\n"
        f"→ https://wems.dev/premium"
    )
