"""Tests for wems-041 multi-source confidence fusion feature."""

import os
import pytest

from wems_mcp_server import WemsServer


@pytest.fixture
def sample_events():
    return [
        {
            "source": "usgs",
            "event_type": "earthquake",
            "title": "M5.2 Offshore",
            "timestamp": "2026-02-22T19:00:00Z",
            "latitude": 34.100,
            "longitude": -118.200,
            "event_id": "usgs-1",
            "url": "https://earthquake.usgs.gov/example/1",
        },
        {
            "source": "nws",
            "event_type": "earthquake",
            "title": "Seismic Alert",
            "timestamp": "2026-02-22T19:15:00Z",
            "latitude": 34.110,
            "longitude": -118.210,
            "event_id": "nws-1",
            "url": "https://api.weather.gov/example/1",
        },
        {
            "source": "cisa",
            "event_type": "earthquake",
            "title": "Infra Advisory",
            "timestamp": "2026-02-22T21:30:00Z",
            "latitude": 40.700,
            "longitude": -74.000,
            "event_id": "cisa-1",
            "url": "https://www.cisa.gov/example/1",
        },
    ]


def test_fusion_clusters_by_time_and_distance(sample_events):
    server = WemsServer()

    incidents = server._fuse_events_to_incidents(
        sample_events,
        fusion_window_minutes=30,
        dedupe_radius_km=25,
    )

    assert len(incidents) == 2
    top = incidents[0]
    assert top["source_count"] == 2
    assert set(top["confidence_breakdown"].keys()) == {"usgs", "nws"}
    assert top["confidence_score"] == pytest.approx((1.0 + 0.95) / (1.0 + 0.9 + 0.95 + 0.85), rel=1e-3)


def test_fusion_ignores_unknown_or_invalid_events(sample_events):
    server = WemsServer()
    sample_events.extend([
        {"source": "unknown", "timestamp": "2026-02-22T19:00:00Z", "latitude": 10, "longitude": 20},
        {"source": "usgs", "timestamp": "bad", "latitude": 10, "longitude": 20},
        {"source": "noaa", "timestamp": "2026-02-22T19:00:00Z", "latitude": None, "longitude": 20},
    ])

    incidents = server._fuse_events_to_incidents(sample_events)
    assert len(incidents) == 2


def test_feature_flag_disabled_by_default(monkeypatch):
    monkeypatch.delenv("WEMS_FEATURE_MULTI_SOURCE_CONFIDENCE_FUSION", raising=False)
    server = WemsServer()
    assert server.feature_flags["multi_source_confidence_fusion"] is False


def test_feature_flag_enabled(monkeypatch):
    monkeypatch.setenv("WEMS_FEATURE_MULTI_SOURCE_CONFIDENCE_FUSION", "true")
    server = WemsServer()
    assert server.feature_flags["multi_source_confidence_fusion"] is True
