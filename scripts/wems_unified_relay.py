#!/usr/bin/env python3
import json
import math
import pathlib
import time
from datetime import datetime, timezone

import requests

CONFIG_PATH = pathlib.Path('/home/bonsaihorn/.openclaw/workspace/pipeline-v2/config/wems_alert_config.json')
STATE_PATH = pathlib.Path('/home/bonsaihorn/.openclaw/workspace/pipeline-v2/reports/weekly/wems_seen_ids.json')
USGS_SIG_URL = 'https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.geojson'
SWPC_ALERTS_URL = 'https://services.swpc.noaa.gov/products/alerts.json'

SEV_ORDER = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}

def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return default
    return default

def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))

def haversine_miles(lat1, lon1, lat2, lon2):
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d1 = math.radians(lat2 - lat1)
    d2 = math.radians(lon2 - lon1)
    a = math.sin(d1/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(d2/2)**2
    return 2*r*math.asin(math.sqrt(a))

def norm_solar_sev(msg):
    m = (msg or '').lower()
    if 'x-class' in m or 'severe' in m:
        return 'high'
    if 'warning' in m or 'alert' in m:
        return 'medium'
    return 'low'

def should_pass_radius(cfg, event_type, lat, lon):
    home = cfg.get('home', {})
    if lat is None or lon is None:
        return True, None
    if home.get('lat') is None or home.get('lon') is None:
        return True, None
    radius = cfg.get('radii_miles', {}).get(event_type)
    if radius is None:
        return True, None
    d = haversine_miles(home['lat'], home['lon'], lat, lon)
    return d <= float(radius), round(d, 2)

def fetch_usgs(session, cfg, seen):
    out = []
    if not cfg['enabled_sources'].get('usgs_earthquake', False):
        return out
    resp = session.get(USGS_SIG_URL, timeout=12)
    resp.raise_for_status()
    features = resp.json().get('features', [])
    min_mag = float(cfg.get('thresholds', {}).get('earthquake_min_mag', 5.0))
    for f in features:
        eid = f.get('id')
        if not eid or eid in seen:
            continue
        p = f.get('properties', {})
        g = f.get('geometry', {})
        mag = float(p.get('mag') or 0)
        if mag < min_mag:
            continue
        coords = g.get('coordinates') or []
        lon = coords[0] if len(coords) > 0 else None
        lat = coords[1] if len(coords) > 1 else None
        ok, dist = should_pass_radius(cfg, 'earthquake', lat, lon)
        if not ok:
            continue
        seen.add(eid)
        out.append({
            'event_id': eid,
            'event_type': 'earthquake',
            'source': 'usgs',
            'severity': 'high' if mag >= 6.5 else 'medium',
            'magnitude': mag,
            'title': p.get('title') or f"M{mag:.1f} earthquake",
            'place': p.get('place'),
            'happened_at': datetime.fromtimestamp((p.get('time') or 0)/1000, tz=timezone.utc).isoformat(),
            'url': p.get('url'),
            'lat': lat,
            'lon': lon,
            'distance_miles': dist,
            'summary': f"🚨 Earthquake M{mag:.1f} — {p.get('place','unknown')}"
        })
    return out

def fetch_swpc(session, cfg, seen):
    out = []
    if not cfg['enabled_sources'].get('swpc_solar', False):
        return out
    resp = session.get(SWPC_ALERTS_URL, timeout=12)
    resp.raise_for_status()
    rows = resp.json() if isinstance(resp.json(), list) else []
    min_sev = cfg.get('thresholds', {}).get('solar_min_severity', 'medium')
    min_rank = SEV_ORDER.get(min_sev, 2)
    for r in rows:
        pid = r.get('product_id')
        if not pid or pid in seen:
            continue
        sev = norm_solar_sev(r.get('message'))
        if SEV_ORDER.get(sev, 1) < min_rank:
            continue
        seen.add(pid)
        out.append({
            'event_id': pid,
            'event_type': 'solar',
            'source': 'swpc',
            'severity': sev,
            'title': f"Space weather alert {pid}",
            'happened_at': r.get('issue_datetime'),
            'url': 'https://www.swpc.noaa.gov/',
            'summary': f"☀️ Space weather {sev.upper()} alert ({pid})"
        })
    return out

def main():
    session = requests.Session()
    seen = set(load_json(STATE_PATH, []))
    last = {'usgs_earthquake': 0, 'swpc_solar': 0}

    while True:
        cfg = load_json(CONFIG_PATH, {})
        poll = cfg.get('source_poll_seconds', {'usgs_earthquake':15,'swpc_solar':60})
        now = time.time()
        events = []
        try:
            if now - last['usgs_earthquake'] >= float(poll.get('usgs_earthquake', 15)):
                events.extend(fetch_usgs(session, cfg, seen))
                last['usgs_earthquake'] = now
            if now - last['swpc_solar'] >= float(poll.get('swpc_solar', 60)):
                events.extend(fetch_swpc(session, cfg, seen))
                last['swpc_solar'] = now
        except Exception:
            pass

        if events:
            hook = cfg.get('relay', {}).get('webhook_url')
            timeout = float(cfg.get('relay', {}).get('timeout_seconds', 10))
            for e in events:
                try:
                    session.post(hook, json=e, timeout=timeout)
                except Exception:
                    pass
            save_json(STATE_PATH, list(seen)[-4000:])

        time.sleep(3)

if __name__ == '__main__':
    main()
