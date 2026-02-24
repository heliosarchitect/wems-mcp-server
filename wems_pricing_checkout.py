"""Pricing + checkout surface helpers for WEMS.

This module is intentionally provider-light and safe by default:
- Reads pricing/checkout metadata from JSON config
- Allows environment override for checkout/customer-portal URLs
- Returns deterministic payloads for MCP/UI surfaces
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


def _default_cfg_path() -> Path:
    return Path(__file__).resolve().parent / "config" / "wems_pricing_checkout.json"


def load_pricing_checkout_config() -> Dict[str, Any]:
    cfg_path = Path(os.environ.get("WEMS_PRICING_CHECKOUT_CONFIG", str(_default_cfg_path())))
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text())
    except Exception:
        return {}


def _env_or(value: Optional[str], fallback: Optional[str]) -> Optional[str]:
    v = (value or "").strip()
    return v if v else fallback


def get_pricing_checkout_surface(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or load_pricing_checkout_config()

    free_cfg = cfg.get("free", {}) if isinstance(cfg, dict) else {}
    pro_cfg = cfg.get("pro", {}) if isinstance(cfg, dict) else {}

    pro_checkout = _env_or(os.environ.get("WEMS_STRIPE_CHECKOUT_URL_PRO"), pro_cfg.get("checkout_url"))
    customer_portal = _env_or(
        os.environ.get("WEMS_STRIPE_CUSTOMER_PORTAL_URL"),
        cfg.get("customer_portal_url"),
    )

    return {
        "currency": cfg.get("currency", "usd"),
        "support_email": cfg.get("support_email", "heliosarchitectlbf@gmail.com"),
        "free": {
            "name": free_cfg.get("name", "Free"),
            "price_monthly": float(free_cfg.get("price_monthly", 0.0) or 0.0),
            "calls_included_rolling_30d": int(free_cfg.get("calls_included_rolling_30d", 5000) or 5000),
            "cta_label": free_cfg.get("cta_label", "Get Started"),
            "cta_href": free_cfg.get("cta_href", "#installation"),
        },
        "pro": {
            "name": pro_cfg.get("name", "Pro"),
            "price_monthly": float(pro_cfg.get("price_monthly", 24.99) or 24.99),
            "checkout_url": pro_checkout,
            "customer_portal_url": customer_portal,
            "cta_label": pro_cfg.get("cta_label", "Start Pro"),
        },
    }


def validate_checkout_surface(surface: Dict[str, Any]) -> Dict[str, Any]:
    pro = surface.get("pro", {}) if isinstance(surface, dict) else {}
    checkout_url = (pro.get("checkout_url") or "").strip()
    customer_portal_url = (pro.get("customer_portal_url") or "").strip()

    issues = []
    if not checkout_url:
        issues.append("missing_pro_checkout_url")
    if customer_portal_url and not customer_portal_url.startswith(("https://", "http://")):
        issues.append("invalid_customer_portal_url")
    if checkout_url and not checkout_url.startswith(("https://", "http://")):
        issues.append("invalid_pro_checkout_url")

    return {
        "ready": len(issues) == 0,
        "issues": issues,
    }
