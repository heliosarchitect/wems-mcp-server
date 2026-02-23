"""Minimal usage tracking shim for WEMS.

Current implementation is intentionally lightweight and local-stdout based,
so it never blocks API execution.
"""

from __future__ import annotations

from datetime import datetime, timezone


def record_api_call(*, license_key=None, tier="free", tool_name="unknown", success=True, error_message=None):
    ts = datetime.now(timezone.utc).isoformat()
    key_hint = "none" if not license_key else "set"
    status = "ok" if success else "error"
    msg = f"[wems_usage] {ts} tier={tier} tool={tool_name} key={key_hint} status={status}"
    if error_message:
        msg += f" err={error_message[:200]}"
    print(msg)
