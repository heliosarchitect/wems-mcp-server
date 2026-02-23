"""Stripe metering helper for WEMS.

Best-effort metering: never blocks core alerting path.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any


def _load_cfg() -> dict:
    cfg_path = os.environ.get(
        "WEMS_STRIPE_BILLING_CONFIG",
        str(Path(__file__).resolve().parent / "config" / "wems_stripe_billing.json"),
    )
    p = Path(cfg_path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _resolve_customer_id(tenant_key: str, cfg: dict) -> Optional[str]:
    mappings = cfg.get("api_key_to_customer", {}) if isinstance(cfg, dict) else {}
    if tenant_key in mappings:
        return mappings[tenant_key]
    # Optional direct pass-through if tenant key itself is a Stripe customer id
    if isinstance(tenant_key, str) and tenant_key.startswith("cus_"):
        return tenant_key
    return cfg.get("default_customer_id")


def estimate_monthly_cost(total_calls_rolling_30d: int, cfg: Optional[Dict[str, Any]] = None) -> float:
    """Estimate cost from pricing tiers using a rolling 30-day window.

    Pricing model:
    - free_calls_per_rolling_30d deducted first (fallback: free_calls_per_month)
    - tiered per-call rates applied progressively
    """
    cfg = cfg or _load_cfg()
    pricing = cfg.get("pricing", {}) if isinstance(cfg, dict) else {}
    free_calls = int(
        pricing.get("free_calls_per_rolling_30d", pricing.get("free_calls_per_month", 0)) or 0
    )
    tiers = pricing.get("tiers", []) or []

    billable = max(0, int(total_calls_rolling_30d) - free_calls)
    if billable <= 0 or not tiers:
        return 0.0

    remaining = billable
    prior_cap = 0
    cost = 0.0

    for tier in tiers:
        up_to = tier.get("up_to_calls")
        rate = float(tier.get("rate_per_call", 0.0) or 0.0)
        if up_to is None:
            cost += remaining * rate
            remaining = 0
            break

        cap = int(up_to)
        tier_size = max(0, cap - prior_cap)
        used = min(remaining, tier_size)
        cost += used * rate
        remaining -= used
        prior_cap = cap
        if remaining <= 0:
            break

    return round(cost, 6)


def emit_meter_event(tenant_key: str, tool_name: str, units: int = 1) -> bool:
    """Emit a Stripe meter event.

    Returns True if sent; False for disabled/not-configured/errors.
    """
    if os.environ.get("WEMS_STRIPE_BILLING_ENABLED", "0").strip().lower() not in {"1", "true", "yes", "on"}:
        return False

    stripe_key = os.environ.get("STRIPE_API_KEY") or os.environ.get("STRIPE_SECRET_KEY")
    if not stripe_key:
        return False

    cfg = _load_cfg()
    event_name = cfg.get("event_name", "wems.api.call")
    customer_id = _resolve_customer_id(tenant_key, cfg)
    if not customer_id:
        return False

    payload = {
        "event_name": event_name,
        "payload[value]": str(max(1, int(units))),
        "payload[stripe_customer_id]": customer_id,
        "identifier": f"wems:{customer_id}:{tool_name}",
    }

    req = urllib.request.Request(
        "https://api.stripe.com/v1/billing/meter_events",
        data=urllib.parse.urlencode(payload).encode(),
    )
    req.add_header("Authorization", f"Bearer {stripe_key}")

    try:
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception:
        return False
