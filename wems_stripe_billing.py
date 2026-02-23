"""Stripe metering helper for WEMS.

Best-effort metering: never blocks core alerting path.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional


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
