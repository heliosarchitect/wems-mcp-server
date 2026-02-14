"""
Test fixtures and configuration for WEMS MCP Server tests.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import pytest
import httpx
import yaml
from mcp.types import TextContent

from wems_mcp_server import WemsServer


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        "alerts": {
            "earthquake": {
                "min_magnitude": 5.0,
                "webhook": "https://webhook.example.com/earthquake"
            },
            "solar": {
                "min_kp_index": 6.0,
                "webhook": "https://webhook.example.com/solar"
            },
            "volcano": {
                "alert_levels": ["WARNING", "WATCH"],
                "webhook": "https://webhook.example.com/volcano"
            },
            "tsunami": {
                "enabled": True,
                "webhook": "https://webhook.example.com/tsunami"
            },
            "hurricane": {
                "enabled": True,
                "webhook": "https://webhook.example.com/hurricane"
            },
            "wildfire": {
                "enabled": True,
                "webhook": "https://webhook.example.com/wildfire"
            },
            "severe_weather": {
                "enabled": True,
                "webhook": "https://webhook.example.com/severe_weather"
            },
            "floods": {
                "enabled": True,
                "webhook": "https://webhook.example.com/floods"
            },
            "air_quality": {
                "enabled": True,
                "webhook": "https://webhook.example.com/air_quality"
            }
        }
    }


@pytest.fixture
def temp_config_file(sample_config):
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(sample_config, f)
        return f.name


@pytest.fixture
def mock_earthquake_response():
    """Mock USGS earthquake API response."""
    return {
        "type": "FeatureCollection",
        "metadata": {
            "generated": int(datetime.now(timezone.utc).timestamp() * 1000),
            "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson",
            "title": "USGS Magnitude 4.5+ Earthquakes, Past Day",
            "status": 200,
            "api": "1.13.6",
            "count": 2
        },
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "mag": 6.2,
                    "place": "15 km SSW of Larsen Bay, Alaska",
                    "time": int((datetime.now(timezone.utc).timestamp() - 3600) * 1000),  # 1 hour ago
                    "updated": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "tz": None,
                    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/us70012345",
                    "detail": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/us70012345.geojson",
                    "felt": None,
                    "cdi": None,
                    "mmi": None,
                    "alert": "green",
                    "status": "reviewed",
                    "tsunami": 0,
                    "sig": 588,
                    "net": "us",
                    "code": "70012345",
                    "ids": ",us70012345,",
                    "sources": ",us,",
                    "types": ",general-text,geoserve,nearby-cities,origin,phase-data,scitech-text,",
                    "nst": None,
                    "dmin": None,
                    "rms": 1.23,
                    "gap": None,
                    "magType": "mww",
                    "type": "earthquake",
                    "title": "M 6.2 - 15 km SSW of Larsen Bay, Alaska"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-153.9726, 57.0129, 10.0]
                },
                "id": "us70012345"
            },
            {
                "type": "Feature",
                "properties": {
                    "mag": 4.8,
                    "place": "42 km NE of Hilo, Hawaii",
                    "time": int((datetime.now(timezone.utc).timestamp() - 7200) * 1000),  # 2 hours ago
                    "updated": int(datetime.now(timezone.utc).timestamp() * 1000),
                    "tz": None,
                    "url": "https://earthquake.usgs.gov/earthquakes/eventpage/hv70012346",
                    "detail": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/detail/hv70012346.geojson",
                    "felt": 5,
                    "cdi": 3.2,
                    "mmi": None,
                    "alert": "green",
                    "status": "automatic",
                    "tsunami": 0,
                    "sig": 351,
                    "net": "hv",
                    "code": "70012346",
                    "ids": ",hv70012346,",
                    "sources": ",hv,",
                    "types": ",general-text,geoserve,nearby-cities,origin,phase-data,",
                    "nst": 25,
                    "dmin": 0.03542,
                    "rms": 0.12,
                    "gap": 85,
                    "magType": "md",
                    "type": "earthquake",
                    "title": "M 4.8 - 42 km NE of Hilo, Hawaii"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [-154.8034, 19.8276, 35.4]
                },
                "id": "hv70012346"
            }
        ],
        "bbox": [-154.8034, 19.8276, 0, -153.9726, 57.0129, 35.4]
    }


@pytest.fixture
def mock_earthquake_empty_response():
    """Mock empty USGS earthquake API response."""
    return {
        "type": "FeatureCollection",
        "metadata": {
            "generated": int(datetime.now(timezone.utc).timestamp() * 1000),
            "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/6.0_day.geojson",
            "title": "USGS Magnitude 6.0+ Earthquakes, Past Day",
            "status": 200,
            "api": "1.13.6",
            "count": 0
        },
        "features": [],
        "bbox": []
    }


@pytest.fixture
def mock_solar_kindex_response():
    """Mock NOAA K-index API response."""
    now = datetime.now(timezone.utc)
    return [
        {
            "time_tag": (now.replace(minute=0, second=0, microsecond=0)).isoformat().replace('+00:00', 'Z'),
            "k_index": 4.0,
            "k_index_flag": "nominal"
        },
        {
            "time_tag": (now.replace(minute=0, second=0, microsecond=0)).isoformat().replace('+00:00', 'Z'),
            "k_index": 7.3,
            "k_index_flag": "nominal"
        }
    ]


@pytest.fixture
def mock_solar_events_response():
    """Mock NOAA space weather events API response."""
    now = datetime.now(timezone.utc)
    return [
        {
            "begin_time": (now - timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "type": "Solar Flare",
            "message": "M2.1 Solar Flare observed from Region 3234",
            "space_weather_message_code": "ALTK05",
            "issue_datetime": now.strftime('%Y-%m-%dT%H:%M:%SZ')
        },
        {
            "begin_time": (now - timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "type": "Geomagnetic Activity",
            "message": "Minor geomagnetic storm conditions observed",
            "space_weather_message_code": "WARK04",
            "issue_datetime": now.strftime('%Y-%m-%dT%H:%M:%SZ')
        }
    ]


@pytest.fixture
def mock_tsunami_response():
    """Mock NOAA tsunami API response."""
    now = datetime.now(timezone.utc)
    return [
        {
            "location": "Near the coast of Central Peru",
            "magnitude": "7.2",
            "time": (now - timedelta(hours=3)).isoformat().replace('+00:00', 'Z'),
            "updated": now.isoformat().replace('+00:00', 'Z'),
            "url": "https://www.tsunami.gov/events/PHEB/2024/02/13/PHEB240213.001.html",
            "status": "active"
        }
    ]


@pytest.fixture
def mock_tsunami_empty_response():
    """Mock empty NOAA tsunami API response."""
    return []


@pytest.fixture
def mock_hurricane_response():
    """Mock NHC CurrentSummaries API response."""
    return {
        "summaries": []
    }


@pytest.fixture 
def mock_hurricane_response_with_storms():
    """Mock NHC CurrentSummaries API response with active storms."""
    return {
        "summaries": [
            {
                "basin": "atlantic",
                "name": "Tropical Storm Alpha",
                "intensity": "Tropical Storm",
                "movement": "NW at 12 mph",
                "location": "25.4N 78.8W"
            },
            {
                "basin": "atlantic", 
                "name": "Hurricane Beta",
                "intensity": "Category 2 Hurricane",
                "movement": "NNW at 15 mph",
                "location": "28.2N 80.1W"
            }
        ]
    }


@pytest.fixture
def mock_hurricane_empty_response():
    """Mock empty NHC CurrentSummaries API response."""
    return {
        "summaries": []
    }


@pytest.fixture
def mock_hurricane_alerts_response():
    """Mock NWS hurricane alerts API response."""
    return {
        "features": [
            {
                "properties": {
                    "headline": "Hurricane Warning issued for South Florida",
                    "areaDesc": "Miami-Dade, Broward Counties"
                }
            },
            {
                "properties": {
                    "headline": "Tropical Storm Watch issued for Central Florida",
                    "areaDesc": "Orange, Seminole Counties"
                }
            }
        ]
    }


@pytest.fixture
def mock_hurricane_alerts_empty_response():
    """Mock empty NWS hurricane alerts API response."""
    return {
        "features": []
    }


@pytest.fixture
def mock_wildfire_alerts_response():
    """Mock NWS fire weather alerts API response."""
    return {
        "features": []
    }


@pytest.fixture
def mock_wildfire_alerts_response_with_alerts():
    """Mock NWS fire weather alerts API response with active alerts."""
    return {
        "features": [
            {
                "properties": {
                    "headline": "Red Flag Warning issued for Central Valley",
                    "areaDesc": "Central Valley, California",
                    "severity": "Extreme"
                }
            },
            {
                "properties": {
                    "headline": "Fire Weather Watch issued for Northern Mountains", 
                    "areaDesc": "Northern Mountains, California",
                    "severity": "Moderate"
                }
            }
        ]
    }


@pytest.fixture
def mock_wildfire_alerts_empty_response():
    """Mock empty NWS fire weather alerts API response."""
    return {
        "features": []
    }


@pytest.fixture
def mock_wildfire_nifc_response():
    """Mock NIFC fire perimeters API response."""
    return {
        "features": [
            {
                "attributes": {
                    "IncidentName": "Wildfire Alpha",
                    "GISAcres": 125000,
                    "PercentContained": 35,
                    "POOState": "CA"
                }
            },
            {
                "attributes": {
                    "IncidentName": "Wildfire Beta", 
                    "GISAcres": 85000,
                    "PercentContained": 60,
                    "POOState": "OR"
                }
            }
        ]
    }


@pytest.fixture
def mock_wildfire_nifc_empty_response():
    """Mock empty NIFC fire perimeters API response."""
    return {
        "features": []
    }


@pytest.fixture
def mock_severe_weather_response():
    """Mock NWS severe weather alerts API response."""
    return {
        "@context": [
            "https://geojson.org/geojson-ld/geojson-context.jsonld",
            {
                "@version": "1.1",
                "wx": "https://api.weather.gov/ontology#",
                "@vocab": "https://api.weather.gov/ontology#"
            }
        ],
        "type": "FeatureCollection",
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.severe.001",
                "type": "Feature",
                "geometry": None,
                "properties": {
                    "@id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.severe.001",
                    "@type": "wx:Alert",
                    "id": "urn:oid:2.49.0.1.840.0.test.severe.001",
                    "areaDesc": "Dallas County; Tarrant County",
                    "geocode": {
                        "SAME": ["048113", "048439"],
                        "UGC": ["TXC113", "TXC439"]
                    },
                    "sent": "2026-02-13T20:00:00+00:00",
                    "effective": "2026-02-13T20:00:00+00:00",
                    "onset": "2026-02-13T20:15:00+00:00",
                    "expires": "2026-02-13T23:00:00+00:00",
                    "status": "Actual",
                    "messageType": "Alert",
                    "category": "Met",
                    "severity": "severe",
                    "certainty": "likely",
                    "urgency": "immediate",
                    "event": "Severe Thunderstorm Warning",
                    "sender": "w-nws.webmaster@noaa.gov",
                    "senderName": "NWS",
                    "headline": "Severe Thunderstorm Warning issued February 13 at 8:00PM CST until February 13 at 11:00PM CST by NWS Fort Worth TX",
                    "description": "At 800 PM CST, a severe thunderstorm was located over Dallas, moving northeast at 45 mph. HAZARD...60 mph wind gusts and quarter size hail. SOURCE...Radar indicated. IMPACT...Hail damage to vehicles is expected. Expect wind damage to roofs, siding, and trees.",
                    "instruction": "For your protection move to an interior room on the lowest floor of a building.",
                    "response": "Shelter"
                }
            }
        ]
    }


@pytest.fixture
def mock_tornado_response():
    """Mock tornado warning response."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.tornado.001",
                "type": "Feature",
                "properties": {
                    "event": "Tornado Warning",
                    "headline": "Tornado Warning issued February 13 at 8:00PM CST",
                    "areaDesc": "Dallas County, TX",
                    "severity": "extreme",
                    "urgency": "immediate",
                    "certainty": "observed",
                    "sent": "2026-02-13T20:00:00+00:00",
                    "expires": "2026-02-13T20:45:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_thunderstorm_response():
    """Mock thunderstorm warning response."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.thunderstorm.001",
                "type": "Feature",
                "properties": {
                    "event": "Severe Thunderstorm Warning",
                    "headline": "Severe Thunderstorm Warning issued February 13 at 8:00PM CST",
                    "areaDesc": "Harris County, TX",
                    "severity": "severe",
                    "urgency": "immediate", 
                    "certainty": "likely",
                    "sent": "2026-02-13T20:00:00+00:00",
                    "expires": "2026-02-13T21:00:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_flood_response():
    """Mock flood warning response."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.flood.001",
                "type": "Feature",
                "properties": {
                    "event": "Flash Flood Warning",
                    "headline": "Flash Flood Warning issued February 13 at 8:00PM CST",
                    "areaDesc": "Travis County, TX",
                    "severity": "severe",
                    "urgency": "immediate",
                    "certainty": "likely",
                    "sent": "2026-02-13T20:00:00+00:00",
                    "expires": "2026-02-13T23:00:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_winter_storm_response():
    """Mock winter storm warning response."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.winter.001",
                "type": "Feature",
                "properties": {
                    "event": "Winter Storm Warning",
                    "headline": "Winter Storm Warning issued February 13 at 8:00PM CST",
                    "areaDesc": "Denver County, CO",
                    "severity": "severe",
                    "urgency": "expected",
                    "certainty": "likely",
                    "sent": "2026-02-13T20:00:00+00:00",
                    "expires": "2026-02-14T12:00:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_severe_weather_all_severities():
    """Mock response with all severity levels."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {
                    "event": "Tornado Warning",
                    "severity": "extreme",
                    "sent": "2026-02-13T20:00:00+00:00",
                    "status": "Actual"
                }
            },
            {
                "properties": {
                    "event": "Thunderstorm Watch",
                    "severity": "moderate",
                    "sent": "2026-02-13T20:00:00+00:00",
                    "status": "Actual"
                }
            },
            {
                "properties": {
                    "event": "Wind Advisory",
                    "severity": "minor",
                    "sent": "2026-02-13T20:00:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_empty_alerts_response():
    """Mock empty alerts response."""
    return {
        "type": "FeatureCollection",
        "features": []
    }


@pytest.fixture
def mock_urgent_alerts_response():
    """Mock alerts with immediate/expected urgency."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {
                    "event": "Flash Flood Warning",
                    "urgency": "immediate",
                    "severity": "severe",
                    "sent": "2026-02-13T20:00:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_certain_alerts_response():
    """Mock alerts with observed/likely certainty."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {
                    "event": "Tornado Warning",
                    "certainty": "observed",
                    "severity": "extreme",
                    "sent": "2026-02-13T20:00:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_many_alerts_response():
    """Mock response with many alerts to test pagination."""
    features = []
    for i in range(10):
        features.append({
            "properties": {
                "event": f"Severe Weather Alert {i+1}",
                "areaDesc": f"County {i+1}",
                "severity": "severe" if i % 2 == 0 else "moderate",
                "urgency": "immediate",
                "certainty": "likely",
                "sent": "2026-02-13T20:00:00+00:00",
                "expires": "2026-02-13T23:00:00+00:00",
                "status": "Actual"
            }
        })
    return {
        "type": "FeatureCollection",
        "features": features
    }


@pytest.fixture
def mock_test_alerts_response():
    """Mock response with test messages that should be filtered."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {
                    "event": "Test Message",
                    "status": "Test",
                    "sent": "2026-02-13T20:00:00+00:00"
                }
            },
            {
                "properties": {
                    "event": "Tornado Warning",
                    "status": "Actual",
                    "severity": "extreme",
                    "sent": "2026-02-13T20:00:00+00:00"
                }
            }
        ]
    }


@pytest.fixture
def mock_old_alerts_response():
    """Mock response with old alerts outside time range."""
    old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat().replace('+00:00', 'Z')
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "properties": {
                    "event": "Old Weather Alert",
                    "severity": "severe",
                    "sent": old_time,
                    "status": "Actual"
                }
            }
        ]
    }


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, json_data: Dict[str, Any], status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code
        self.headers = {'content-type': 'application/json'}

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                message=f"HTTP {self.status_code}",
                request=None,
                response=self
            )


@pytest.fixture
async def wems_server(temp_config_file):
    """Create a WEMS server instance for testing (free tier)."""
    server = WemsServer(temp_config_file)
    yield server
    await server.http_client.aclose()


@pytest.fixture
async def wems_server_default():
    """Create a WEMS server instance with default config (free tier)."""
    server = WemsServer()  # No config file - uses defaults
    yield server
    await server.http_client.aclose()


@pytest.fixture
async def wems_server_premium(temp_config_file, monkeypatch):
    """Create a WEMS server instance with premium tier."""
    monkeypatch.setenv("WEMS_API_KEY", "test_premium_key")
    monkeypatch.setenv("WEMS_PREMIUM_KEYS", "test_premium_key")
    server = WemsServer(temp_config_file)
    assert server.tier == "premium", f"Expected premium tier, got {server.tier}"
    yield server
    await server.http_client.aclose()


@pytest.fixture
async def wems_server_free(temp_config_file, monkeypatch):
    """Create a WEMS server instance explicitly on free tier."""
    monkeypatch.delenv("WEMS_API_KEY", raising=False)
    monkeypatch.delenv("WEMS_PREMIUM_KEYS", raising=False)
    server = WemsServer(temp_config_file)
    assert server.tier == "free", f"Expected free tier, got {server.tier}"
    yield server
    await server.http_client.aclose()


@pytest.fixture
async def wems_server_with_alerts(temp_config_file, monkeypatch):
    """Create a WEMS server instance with alerts configured."""
    monkeypatch.setenv("WEMS_API_KEY", "test_premium_key")
    monkeypatch.setenv("WEMS_PREMIUM_KEYS", "test_premium_key")
    server = WemsServer(temp_config_file)
    assert server.tier == "premium", f"Expected premium tier, got {server.tier}"
    yield server
    await server.http_client.aclose()


@pytest.fixture
def mock_flood_alerts_response():
    """Mock flood alerts response from NWS API."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.flood.001",
                "type": "Feature",
                "properties": {
                    "event": "Flood Warning",
                    "headline": "Flood Warning issued February 13 at 8:00PM CST until February 14 at 8:00AM CST",
                    "areaDesc": "Harris County, TX",
                    "severity": "moderate",
                    "urgency": "expected",
                    "certainty": "likely",
                    "sent": "2026-02-13T20:00:00+00:00",
                    "expires": "2026-02-14T08:00:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_flash_flood_warning_response():
    """Mock flash flood warning response."""
    return {
        "type": "FeatureCollection", 
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.flashflood.001",
                "type": "Feature",
                "properties": {
                    "event": "Flash Flood Warning",
                    "headline": "Flash Flood Warning issued February 13 at 8:00PM CST until February 13 at 11:00PM CST",
                    "areaDesc": "Travis County, TX",
                    "severity": "severe",
                    "urgency": "immediate",
                    "certainty": "observed",
                    "sent": "2026-02-13T20:00:00+00:00",
                    "expires": "2026-02-13T23:00:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_flood_warning_response():
    """Mock flood warning response."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.flood.002",
                "type": "Feature", 
                "properties": {
                    "event": "Flood Warning",
                    "headline": "Flood Warning issued February 13 at 6:00PM CST until February 15 at 6:00AM CST",
                    "areaDesc": "Brazos County, TX",
                    "severity": "moderate",
                    "urgency": "expected", 
                    "certainty": "likely",
                    "sent": "2026-02-13T18:00:00+00:00",
                    "expires": "2026-02-15T06:00:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_flood_watch_response():
    """Mock flood watch response."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.floodwatch.001",
                "type": "Feature",
                "properties": {
                    "event": "Flash Flood Watch",
                    "headline": "Flash Flood Watch issued February 13 at 5:00PM CST until February 14 at 5:00AM CST",
                    "areaDesc": "Montgomery County, TX",
                    "severity": "minor",
                    "urgency": "future",
                    "certainty": "possible",
                    "sent": "2026-02-13T17:00:00+00:00",
                    "expires": "2026-02-14T05:00:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_flood_advisory_response():
    """Mock flood advisory response."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.floodadvisory.001",
                "type": "Feature", 
                "properties": {
                    "event": "Flood Advisory",
                    "headline": "Flood Advisory issued February 13 at 7:00PM CST until February 14 at 2:00AM CST",
                    "areaDesc": "Fort Bend County, TX",
                    "severity": "minor",
                    "urgency": "expected",
                    "certainty": "likely",
                    "sent": "2026-02-13T19:00:00+00:00", 
                    "expires": "2026-02-14T02:00:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_major_flood_warning_response():
    """Mock major flood warning response."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "id": "https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.majorflood.001",
                "type": "Feature",
                "properties": {
                    "event": "Flash Flood Warning",
                    "headline": "Flash Flood Emergency issued February 13 at 8:30PM CST until February 14 at 2:00AM CST",
                    "areaDesc": "Downtown Houston, TX",
                    "severity": "extreme",
                    "urgency": "immediate",
                    "certainty": "observed",
                    "sent": "2026-02-13T20:30:00+00:00",
                    "expires": "2026-02-14T02:00:00+00:00",
                    "status": "Actual"
                }
            }
        ]
    }


@pytest.fixture
def mock_usgs_river_gauges_response():
    """Mock USGS river gauges response."""
    return {
        "name": "NWIS Site Data",
        "declaredType": "org.cuahsi.waterml.TimeSeriesResponseType",
        "scope": "javax.xml.bind.JAXBElement$GlobalScope",
        "value": {
            "timeSeries": [
                {
                    "sourceInfo": {
                        "siteName": "BRAZOS RIVER AT RICHMOND, TX",
                        "siteCode": [
                            {
                                "value": "08116650",
                                "network": "NWIS",
                                "agencyCode": "USGS"
                            }
                        ]
                    },
                    "variable": {
                        "variableName": "Gage height, ft",
                        "variableCode": [
                            {
                                "value": "00065",
                                "network": "NWIS"
                            }
                        ],
                        "unit": {
                            "unitCode": "ft"
                        }
                    },
                    "values": [
                        {
                            "value": [
                                {
                                    "value": "22.45",
                                    "qualifiers": "A",
                                    "dateTime": "2026-02-13T20:00:00.000-06:00"
                                },
                                {
                                    "value": "22.52",
                                    "qualifiers": "A", 
                                    "dateTime": "2026-02-13T20:15:00.000-06:00"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }


@pytest.fixture  
def mock_large_flood_response():
    """Mock response with many flood events to test pagination."""
    features = []
    for i in range(10):
        features.append({
            "id": f"https://api.weather.gov/alerts/urn:oid:2.49.0.1.840.0.test.flood.{i:03d}",
            "type": "Feature",
            "properties": {
                "event": "Flood Warning" if i % 2 == 0 else "Flash Flood Warning",
                "headline": f"Flood Warning {i+1} issued February 13",
                "areaDesc": f"County {i+1}, TX",
                "severity": "moderate" if i % 2 == 0 else "severe",
                "urgency": "expected",
                "certainty": "likely", 
                "sent": "2026-02-13T20:00:00+00:00",
                "expires": "2026-02-14T08:00:00+00:00",
                "status": "Actual"
            }
        })
    
    return {
        "type": "FeatureCollection",
        "features": features
    }


@pytest.fixture
def mock_empty_response():
    """Mock empty response for APIs."""
    return {
        "type": "FeatureCollection",
        "features": []
    }


@pytest.fixture
def mock_air_quality_response():
    """Mock OpenAQ locations response with air quality measurements."""
    return {
        "meta": {"name": "openaq-api", "limit": 10, "page": 1, "found": 2},
        "results": [
            {
                "id": 1001,
                "name": "Downtown LA Monitor",
                "locality": "Los Angeles",
                "country": {"code": "US", "name": "United States"},
                "coordinates": {"latitude": 34.0522, "longitude": -118.2437},
                "latest": {"value": 42.3, "datetime": "2026-02-13T20:00:00Z"},
            },
            {
                "id": 1002,
                "name": "Pasadena Station",
                "locality": "Pasadena",
                "country": {"code": "US", "name": "United States"},
                "coordinates": {"latitude": 34.1478, "longitude": -118.1445},
                "latest": {"value": 55.1, "datetime": "2026-02-13T19:45:00Z"},
            },
        ]
    }


@pytest.fixture
def mock_air_quality_empty_response():
    """Mock empty OpenAQ response."""
    return {
        "meta": {"name": "openaq-api", "limit": 10, "page": 1, "found": 0},
        "results": []
    }


@pytest.fixture
def mock_air_quality_hazardous_response():
    """Mock OpenAQ response with hazardous AQI values."""
    return {
        "meta": {"name": "openaq-api", "limit": 10, "page": 1, "found": 1},
        "results": [
            {
                "id": 2001,
                "name": "Industrial Zone Sensor",
                "locality": "Houston",
                "country": {"code": "US", "name": "United States"},
                "coordinates": {"latitude": 29.7604, "longitude": -95.3698},
                "latest": {"value": 350.0, "datetime": "2026-02-13T20:00:00Z"},
            }
        ]
    }


@pytest.fixture
def mock_air_quality_multi_parameter_response():
    """Mock OpenAQ response for multiple pollutant parameters."""
    return {
        "meta": {"name": "openaq-api", "limit": 10, "page": 1, "found": 1},
        "results": [
            {
                "id": 3001,
                "name": "Multi-Sensor Station",
                "locality": "Denver",
                "country": {"code": "US", "name": "United States"},
                "coordinates": {"latitude": 39.7392, "longitude": -104.9903},
                "latest": {"value": 78.5, "datetime": "2026-02-13T20:00:00Z"},
            }
        ]
    }


@pytest.fixture
def mock_air_quality_locations_response():
    """Mock OpenAQ locations response for coordinate-based search."""
    return {
        "meta": {"name": "openaq-api", "limit": 10, "page": 1, "found": 2},
        "results": [
            {
                "id": 4001,
                "name": "Nearby Station Alpha",
                "locality": "San Francisco",
                "country": {"code": "US", "name": "United States"},
                "coordinates": {"latitude": 37.7749, "longitude": -122.4194},
            },
            {
                "id": 4002,
                "name": "Nearby Station Beta",
                "locality": "Oakland",
                "country": {"code": "US", "name": "United States"},
                "coordinates": {"latitude": 37.8044, "longitude": -122.2712},
            },
        ]
    }


@pytest.fixture
def mock_air_quality_measurements_response():
    """Mock OpenAQ measurements response for a specific location."""
    return {
        "meta": {"name": "openaq-api", "limit": 1, "page": 1, "found": 1},
        "results": [
            {
                "value": 65.2,
                "datetime": {"utc": "2026-02-13T20:00:00Z"},
                "parameter": {"id": 2, "name": "pm25"},
            }
        ]
    }


@pytest.fixture
def mock_air_quality_many_stations_response():
    """Mock OpenAQ response with many stations to test pagination."""
    results = []
    for i in range(10):
        results.append({
            "id": 5000 + i,
            "name": f"Station {i+1}",
            "locality": f"City {i+1}",
            "country": {"code": "US", "name": "United States"},
            "coordinates": {"latitude": 34.0 + i * 0.1, "longitude": -118.0 + i * 0.1},
            "latest": {"value": 30.0 + i * 15, "datetime": "2026-02-13T20:00:00Z"},
        })
    return {
        "meta": {"name": "openaq-api", "limit": 10, "page": 1, "found": 10},
        "results": results
    }


def assert_textcontent_result(result, expected_content_contains=None, expected_count=1):
    """Helper function to assert TextContent results."""
    assert isinstance(result, list)
    assert len(result) == expected_count

    for item in result:
        assert isinstance(item, TextContent)
        assert item.type == "text"
        assert isinstance(item.text, str)

        if expected_content_contains:
            if isinstance(expected_content_contains, str):
                assert expected_content_contains in item.text
            elif isinstance(expected_content_contains, list):
                for content in expected_content_contains:
                    assert content in item.text