"""License helpers for WEMS.

Supports simple key-shape validation and environment-backed expiration checks.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timezone

KEY_RE = re.compile(r"^WEMS-[A-Z0-9]{4}(?:-[A-Z0-9]{4}){3}$")


def is_license_key(value: str) -> bool:
    return bool(value and KEY_RE.match(value.strip()))


def validate_license_key(key: str) -> dict:
    if not is_license_key(key):
        return {"valid": False, "expired": False, "tier": "free", "reason": "invalid_format"}

    # Optional env override for local testing, e.g.:
    # WEMS_LICENSE_TIER=enterprise, WEMS_LICENSE_EXPIRES=2099-01-01T00:00:00Z
    tier = os.environ.get("WEMS_LICENSE_TIER", "premium").lower()
    expires_raw = os.environ.get("WEMS_LICENSE_EXPIRES", "2099-01-01T00:00:00Z")
    try:
        expires = datetime.fromisoformat(expires_raw.replace("Z", "+00:00"))
    except Exception:
        expires = datetime(2099, 1, 1, tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    expired = now >= expires
    return {
        "valid": True,
        "expired": expired,
        "tier": tier if tier in {"free", "premium", "enterprise"} else "premium",
        "expires": expires.isoformat(),
    }
