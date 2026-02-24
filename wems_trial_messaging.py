"""Trial lifecycle messaging hooks for WEMS monetization.

Implements day-3/day-10/day-13 trial touchpoints with safe defaults:
- Disabled by default
- Best-effort only (never blocks request path)
- Quiet-hours guard
- Per-tenant dedupe state
"""

from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class TrialTouchpoint:
    day: int
    days_remaining: int


def _load_cfg() -> Dict[str, Any]:
    cfg_path = os.environ.get(
        "WEMS_TRIAL_MESSAGING_CONFIG",
        str(Path(__file__).resolve().parent / "config" / "wems_trial_messaging.json"),
    )
    p = Path(cfg_path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _enabled(cfg: Dict[str, Any]) -> bool:
    env = os.environ.get("WEMS_TRIAL_MESSAGING_ENABLED")
    if env is not None:
        return env.strip().lower() in {"1", "true", "yes", "on"}
    return bool(cfg.get("enabled", False))


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _resolve_trial_start(api_key: str, cfg: Dict[str, Any]) -> Optional[datetime]:
    env_start = _parse_dt(os.environ.get("WEMS_TRIAL_STARTED_AT"))
    if env_start:
        return env_start

    by_key = cfg.get("trial_start_by_api_key", {}) if isinstance(cfg, dict) else {}
    if api_key and api_key in by_key:
        return _parse_dt(by_key.get(api_key))

    return _parse_dt(cfg.get("default_trial_started_at"))


def _in_quiet_hours(now_local: datetime, quiet_hours_local: list[str]) -> bool:
    if len(quiet_hours_local) != 2:
        return False
    try:
        sh, sm = [int(x) for x in quiet_hours_local[0].split(":", 1)]
        eh, em = [int(x) for x in quiet_hours_local[1].split(":", 1)]
        start = sh * 60 + sm
        end = eh * 60 + em
        cur = now_local.hour * 60 + now_local.minute
    except Exception:
        return False

    if start == end:
        return False
    if start < end:
        return start <= cur < end
    return cur >= start or cur < end


def _current_touchpoint(*, trial_start: datetime, now: datetime, trial_days: int, touchpoints: list[int]) -> Optional[TrialTouchpoint]:
    if now < trial_start:
        return None
    elapsed_days = (now.date() - trial_start.date()).days
    day = elapsed_days + 1
    if day not in set(int(d) for d in touchpoints):
        return None
    return TrialTouchpoint(day=day, days_remaining=max(0, int(trial_days) - day))


def _state_path(cfg: Dict[str, Any]) -> Path:
    configured = cfg.get("state_file")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parent / "build" / "trial_lifecycle_state.json"


def _load_state(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def _save_state(path: Path, state: Dict[str, Any]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, sort_keys=True))
    except Exception:
        pass


def emit_trial_lifecycle_message(
    *,
    api_key: str,
    tier: str,
    tool_name: str,
    rate_remaining: Optional[int] = None,
    now: Optional[datetime] = None,
) -> bool:
    """Emit day-based trial lifecycle messaging hooks.

    Returns True when at least one hook was successfully sent.
    Returns False for disabled/not-due/no-hook/error cases.
    """
    cfg = _load_cfg()
    if not _enabled(cfg):
        return False

    trial_start = _resolve_trial_start(api_key, cfg)
    if not trial_start:
        return False

    now_utc = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    trial_days = int(cfg.get("trial_days", 14) or 14)
    touchpoints = cfg.get("touchpoints", [3, 10, 13])
    touchpoint = _current_touchpoint(
        trial_start=trial_start,
        now=now_utc,
        trial_days=trial_days,
        touchpoints=touchpoints,
    )
    if not touchpoint:
        return False

    tz_name = cfg.get("timezone", "America/New_York")
    try:
        local_now = now_utc.astimezone(ZoneInfo(tz_name))
    except Exception:
        local_now = now_utc

    if _in_quiet_hours(local_now, cfg.get("quiet_hours_local", ["23:00", "07:00"])):
        return False

    key = api_key or "anonymous"
    path = _state_path(cfg)
    state = _load_state(path)
    sent_days = set(state.get(key, {}).get("sent_days", []))
    if touchpoint.day in sent_days:
        return False

    hooks = cfg.get("messaging_hooks", {}) if isinstance(cfg, dict) else {}
    channels = cfg.get("channels", ["email", "in_app"])

    cta_url = cfg.get("default_cta_url", "https://wems.dev/premium")
    payload = {
        "event": "trial_lifecycle_touchpoint",
        "tenant_key": key,
        "tier": tier,
        "touchpoint_day": touchpoint.day,
        "days_remaining": touchpoint.days_remaining,
        "trial_days": trial_days,
        "last_tool": tool_name,
        "rate_remaining": rate_remaining,
        "cta_url": cta_url,
        "timestamp": now_utc.isoformat(),
        "value_snapshot": {
            "day": touchpoint.day,
            "days_remaining": touchpoint.days_remaining,
            "rate_remaining": rate_remaining,
        },
    }

    sent_any = False
    for channel in channels:
        url = hooks.get(channel)
        if not isinstance(url, str) or not url.startswith(("http://", "https://")):
            continue
        req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("User-Agent", "WEMS/TrialLifecycle")
        try:
            with urllib.request.urlopen(req, timeout=5):
                sent_any = True
        except Exception:
            continue

    if sent_any:
        entry = state.get(key, {})
        entry.setdefault("sent_days", [])
        entry["sent_days"] = sorted(set(entry["sent_days"] + [touchpoint.day]))
        entry["updated_at"] = now_utc.isoformat()
        state[key] = entry
        _save_state(path, state)

    return sent_any
