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
            },
            "threat_advisories": {
                "enabled": True,
                "webhook": "https://webhook.example.com/threat_advisories"
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
    """Mock NOAA Tsunami Warning Center Atom XML response with an active warning."""
    now = datetime.now(timezone.utc)
    updated_str = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    event_str = (now - timedelta(hours=3)).strftime('%Y-%m-%dT%H:%M:%SZ')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">\n'
        '  <title>Tsunami Information</title>\n'
        f'  <updated>{updated_str}</updated>\n'
        '  <entry>\n'
        '    <title>Near the coast of Central Peru</title>\n'
        f'    <updated>{event_str}</updated>\n'
        '    <summary type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">Magnitude 7.2 earthquake near Peru coast</div></summary>\n'
        '    <geo:lat>-12.100</geo:lat>\n'
        '    <geo:long>-77.000</geo:long>\n'
        '  </entry>\n'
        '</feed>\n'
    )


@pytest.fixture
def mock_tsunami_empty_response():
    """Mock empty NOAA Tsunami Warning Center Atom XML response."""
    now = datetime.now(timezone.utc)
    updated_str = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">\n'
        '  <title>Tsunami Information</title>\n'
        f'  <updated>{updated_str}</updated>\n'
        '</feed>\n'
    )


@pytest.fixture
def mock_hurricane_response():
    """Mock NHC RSS XML response — no active storms."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:nhc="https://www.nhc.noaa.gov">\n'
        '  <channel>\n'
        '    <title>NHC Atlantic Tropical Cyclones</title>\n'
        '  </channel>\n'
        '</rss>\n'
    )


@pytest.fixture 
def mock_hurricane_response_with_storms():
    """Mock NHC RSS XML response with active storms."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:nhc="https://www.nhc.noaa.gov">\n'
        '  <channel>\n'
        '    <title>NHC Atlantic Tropical Cyclones</title>\n'
        '    <item>\n'
        '      <title>Tropical Storm Alpha</title>\n'
        '      <description>Tropical Storm Alpha advisory</description>\n'
        '      <link>https://www.nhc.noaa.gov/alpha</link>\n'
        '      <pubDate>Thu, 13 Feb 2026 20:00:00 GMT</pubDate>\n'
        '      <nhc:center>25.4N 78.8W</nhc:center>\n'
        '      <nhc:movement>NW at 12 mph</nhc:movement>\n'
        '      <nhc:wind>65 mph</nhc:wind>\n'
        '      <nhc:pressure>998 mb</nhc:pressure>\n'
        '    </item>\n'
        '    <item>\n'
        '      <title>Hurricane Beta</title>\n'
        '      <description>Hurricane Beta advisory</description>\n'
        '      <link>https://www.nhc.noaa.gov/beta</link>\n'
        '      <pubDate>Thu, 13 Feb 2026 20:00:00 GMT</pubDate>\n'
        '      <nhc:center>28.2N 80.1W</nhc:center>\n'
        '      <nhc:movement>NNW at 15 mph</nhc:movement>\n'
        '      <nhc:wind>105 mph</nhc:wind>\n'
        '      <nhc:pressure>965 mb</nhc:pressure>\n'
        '    </item>\n'
        '  </channel>\n'
        '</rss>\n'
    )


@pytest.fixture
def mock_hurricane_empty_response():
    """Mock empty NHC RSS XML response."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:nhc="https://www.nhc.noaa.gov">\n'
        '  <channel>\n'
        '    <title>NHC Atlantic Tropical Cyclones</title>\n'
        '  </channel>\n'
        '</rss>\n'
    )


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
    """Mock HTTP response for testing.

    Accepts either a dict/list (JSON response) or a plain string
    (XML / pipe-delimited text).  When *json_data* is a string the
    response behaves like a text endpoint: ``.text`` returns the raw
    string and ``.json()`` raises ``ValueError``.
    """

    def __init__(self, json_data, status_code: int = 200):
        self.status_code = status_code

        if isinstance(json_data, str):
            self.text = json_data
            self._json = None
            self.headers = {'content-type': 'text/plain'}
        else:
            self._json = json_data
            self.text = json.dumps(json_data)
            self.headers = {'content-type': 'application/json'}

    def json(self):
        if self._json is None:
            raise ValueError("Response is not JSON")
        return self._json

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
    """Mock EPA AirNow pipe-delimited response with air quality data."""
    # Fields: date|date|time|tz|offset|observed|current|city|state|lat|lon|parameter|aqi|category|...
    return (
        "02/13/26|02/12/26||PST|-8|Y|Y|Los Angeles|CA|34.0522|-118.2437|PM2.5|42|Good|No||SCAQMD\n"
        "02/13/26|02/12/26||PST|-8|Y|Y|Los Angeles|CA|34.0522|-118.2437|Ozone|38|Good|No||SCAQMD\n"
        "02/13/26|02/12/26||PST|-8|Y|Y|Pasadena|CA|34.1478|-118.1445|PM2.5|55|Moderate|No||SCAQMD\n"
    )


@pytest.fixture
def mock_air_quality_empty_response():
    """Mock empty AirNow response (header only, no data lines matching)."""
    return ""


@pytest.fixture
def mock_air_quality_hazardous_response():
    """Mock AirNow response with hazardous AQI values."""
    return (
        "02/13/26|02/12/26||CST|-6|Y|Y|Houston|TX|29.7604|-95.3698|PM2.5|350|Hazardous|Yes||TCEQ\n"
    )


@pytest.fixture
def mock_air_quality_multi_parameter_response():
    """Mock AirNow response with multiple pollutant parameters."""
    return (
        "02/13/26|02/12/26||MST|-7|Y|Y|Denver|CO|39.7392|-104.9903|PM2.5|78|Moderate|No||CDPHE\n"
        "02/13/26|02/12/26||MST|-7|Y|Y|Denver|CO|39.7392|-104.9903|PM10|65|Moderate|No||CDPHE\n"
        "02/13/26|02/12/26||MST|-7|Y|Y|Denver|CO|39.7392|-104.9903|Ozone|45|Good|No||CDPHE\n"
        "02/13/26|02/12/26||MST|-7|Y|Y|Denver|CO|39.7392|-104.9903|NO2|30|Good|No||CDPHE\n"
        "02/13/26|02/12/26||MST|-7|Y|Y|Denver|CO|39.7392|-104.9903|SO2|15|Good|No||CDPHE\n"
        "02/13/26|02/12/26||MST|-7|Y|Y|Denver|CO|39.7392|-104.9903|CO|8|Good|No||CDPHE\n"
    )


@pytest.fixture
def mock_air_quality_locations_response():
    """Mock AirNow response for coordinate-based search near San Francisco."""
    return (
        "02/13/26|02/12/26||PST|-8|Y|Y|San Francisco|CA|37.7749|-122.4194|PM2.5|65|Moderate|No||BAAQMD\n"
        "02/13/26|02/12/26||PST|-8|Y|Y|Oakland|CA|37.8044|-122.2712|PM2.5|58|Moderate|No||BAAQMD\n"
    )


@pytest.fixture
def mock_air_quality_measurements_response():
    """Mock AirNow measurements response (same format — kept for compat)."""
    return (
        "02/13/26|02/12/26||PST|-8|Y|Y|San Francisco|CA|37.7749|-122.4194|PM2.5|65|Moderate|No||BAAQMD\n"
    )


@pytest.fixture
def mock_air_quality_many_stations_response():
    """Mock AirNow response with many stations to test pagination."""
    lines = []
    cities = [
        ("Los Angeles", "CA", 34.0, -118.0),
        ("San Diego", "CA", 32.7, -117.2),
        ("San Jose", "CA", 37.3, -121.9),
        ("Fresno", "CA", 36.7, -119.8),
        ("Sacramento", "CA", 38.6, -121.5),
        ("Oakland", "CA", 37.8, -122.3),
        ("Bakersfield", "CA", 35.4, -119.0),
        ("Riverside", "CA", 33.9, -117.4),
        ("Stockton", "CA", 38.0, -121.3),
        ("Modesto", "CA", 37.6, -121.0),
    ]
    for i, (city, st, lat, lon) in enumerate(cities):
        aqi = 30 + i * 15
        cat = "Good" if aqi <= 50 else "Moderate" if aqi <= 100 else "Unhealthy for Sensitive Groups" if aqi <= 150 else "Unhealthy"
        lines.append(f"02/13/26|02/12/26||PST|-8|Y|Y|{city}|{st}|{lat}|{lon}|PM2.5|{aqi}|{cat}|No||EPA")
    return "\n".join(lines) + "\n"


@pytest.fixture
def mock_dhs_ntas_response():
    """Mock DHS NTAS XML response with active terrorism advisories."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<alerts>\n'
        '<alert start="2026/01/15 14:00" end="2026/07/15 14:00" '
        'type="Elevated Threat" '
        'link="https://www.dhs.gov/ntas/advisory/elevated-threat-2026">\n'
        '<summary><![CDATA[DHS has issued an elevated threat advisory due to the current global security environment.]]></summary>\n'
        '<details><![CDATA[<p>The United States remains in a heightened threat environment.</p>]]></details>\n'
        '<locations>\n'
        '<location><![CDATA[United States]]></location>\n'
        '</locations>\n'
        '<sectors>\n'
        '<sector><![CDATA[Transportation]]></sector>\n'
        '<sector><![CDATA[Critical Infrastructure]]></sector>\n'
        '</sectors>\n'
        '<duration><![CDATA[Until July 15, 2026]]></duration>\n'
        '</alert>\n'
        '</alerts>\n'
    )


@pytest.fixture
def mock_dhs_ntas_imminent_response():
    """Mock DHS NTAS XML with imminent threat."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<alerts>\n'
        '<alert start="2026/02/13 10:00" end="2026/02/20 10:00" '
        'type="Imminent Threat" '
        'link="https://www.dhs.gov/ntas/advisory/imminent-threat-2026">\n'
        '<summary><![CDATA[DHS has issued an imminent threat advisory based on credible intelligence.]]></summary>\n'
        '<details><![CDATA[<p>Credible threat information indicates potential attacks.</p>]]></details>\n'
        '<locations>\n'
        '<location><![CDATA[Major metropolitan areas]]></location>\n'
        '<location><![CDATA[Transportation hubs]]></location>\n'
        '</locations>\n'
        '<sectors>\n'
        '<sector><![CDATA[Transportation]]></sector>\n'
        '</sectors>\n'
        '</alert>\n'
        '</alerts>\n'
    )


@pytest.fixture
def mock_state_dept_travel_response():
    """Mock State Dept travel advisories RSS response."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss xmlns:dc="http://purl.org/dc/elements/1.1/" version="2.0">\n'
        '  <channel>\n'
        '    <title>travel.state.gov: Travel Advisories</title>\n'
        '    <item>\n'
        '      <title>Afghanistan - Level 4: Do Not Travel</title>\n'
        '      <link>https://travel.state.gov/content/travel/en/traveladvisories/af.html</link>\n'
        '      <pubDate>Mon, 10 Feb 2026</pubDate>\n'
        '      <description><![CDATA[Do not travel to Afghanistan due to armed conflict, terrorism, and kidnapping.]]></description>\n'
        '      <category domain="Threat-Level">Level 4: Do Not Travel</category>\n'
        '      <category domain="Country-Tag">AF</category>\n'
        '      <category domain="Keyword">advisory</category>\n'
        '    </item>\n'
        '    <item>\n'
        '      <title>Iraq - Level 4: Do Not Travel</title>\n'
        '      <link>https://travel.state.gov/content/travel/en/traveladvisories/iq.html</link>\n'
        '      <pubDate>Thu, 06 Feb 2026</pubDate>\n'
        '      <description><![CDATA[Do not travel to Iraq due to terrorism, kidnapping, and armed conflict.]]></description>\n'
        '      <category domain="Threat-Level">Level 4: Do Not Travel</category>\n'
        '      <category domain="Country-Tag">IQ</category>\n'
        '      <category domain="Keyword">advisory</category>\n'
        '    </item>\n'
        '    <item>\n'
        '      <title>Mexico - Level 2: Exercise Increased Caution</title>\n'
        '      <link>https://travel.state.gov/content/travel/en/traveladvisories/mx.html</link>\n'
        '      <pubDate>Wed, 05 Feb 2026</pubDate>\n'
        '      <description><![CDATA[Exercise increased caution in Mexico due to crime and kidnapping.]]></description>\n'
        '      <category domain="Threat-Level">Level 2: Exercise Increased Caution</category>\n'
        '      <category domain="Country-Tag">MX</category>\n'
        '      <category domain="Keyword">advisory</category>\n'
        '    </item>\n'
        '    <item>\n'
        '      <title>Canada - Level 1: Exercise Normal Precautions</title>\n'
        '      <link>https://travel.state.gov/content/travel/en/traveladvisories/ca.html</link>\n'
        '      <pubDate>Mon, 03 Feb 2026</pubDate>\n'
        '      <description><![CDATA[Exercise normal precautions in Canada.]]></description>\n'
        '      <category domain="Threat-Level">Level 1: Exercise Normal Precautions</category>\n'
        '      <category domain="Country-Tag">CA</category>\n'
        '      <category domain="Keyword">advisory</category>\n'
        '    </item>\n'
        '  </channel>\n'
        '</rss>\n'
    )


@pytest.fixture
def mock_threat_advisories_empty_response():
    """Mock empty DHS NTAS response - no active threats."""
    return '<?xml version="1.0" encoding="UTF-8"?>\n<alerts>\n</alerts>\n'


@pytest.fixture
def mock_state_dept_empty_response():
    """Mock empty State Dept travel RSS response."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        '  <channel>\n'
        '    <title>travel.state.gov: Travel Advisories</title>\n'
        '  </channel>\n'
        '</rss>\n'
    )


@pytest.fixture
def mock_elevated_threat_response():
    """Mock elevated DHS NTAS response."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<alerts>\n'
        '<alert start="2026/02/01 00:00" end="2026/08/01 00:00" '
        'type="Elevated Threat" '
        'link="https://www.dhs.gov/ntas/advisory/elevated-2026">\n'
        '<summary><![CDATA[The United States remains in a heightened threat environment.]]></summary>\n'
        '<details><![CDATA[Multiple factors contribute to the current threat environment.]]></details>\n'
        '<locations>\n'
        '<location><![CDATA[United States]]></location>\n'
        '</locations>\n'
        '<sectors>\n'
        '<sector><![CDATA[All sectors]]></sector>\n'
        '</sectors>\n'
        '</alert>\n'
        '</alerts>\n'
    )


@pytest.fixture
def mock_many_travel_advisories_response():
    """Mock State Dept response with many advisories to test pagination."""
    items = []
    countries = [
        ("Afghanistan", "AF", 4), ("Iraq", "IQ", 4), ("Syria", "SY", 4),
        ("Somalia", "SO", 4), ("Yemen", "YE", 4), ("Libya", "LY", 4),
        ("South Sudan", "SS", 4), ("Mali", "ML", 4), ("Central African Republic", "CF", 4),
        ("North Korea", "KP", 4), ("Iran", "IR", 4), ("Venezuela", "VE", 4),
    ]
    for name, code, level in countries:
        items.append(
            f'    <item>\n'
            f'      <title>{name} - Level {level}: Do Not Travel</title>\n'
            f'      <link>https://travel.state.gov/content/travel/en/traveladvisories/{code.lower()}.html</link>\n'
            f'      <pubDate>Mon, 10 Feb 2026</pubDate>\n'
            f'      <description><![CDATA[Do not travel to {name}.]]></description>\n'
            f'      <category domain="Threat-Level">Level {level}: Do Not Travel</category>\n'
            f'      <category domain="Country-Tag">{code}</category>\n'
            f'    </item>\n'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        '  <channel>\n'
        '    <title>travel.state.gov: Travel Advisories</title>\n'
        + ''.join(items) +
        '  </channel>\n'
        '</rss>\n'
    )


@pytest.fixture
def mock_cyber_advisories_response():
    """Mock CISA cyber advisories RSS response."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        '  <channel>\n'
        '    <title>CISA Cybersecurity Advisories</title>\n'
        '    <item>\n'
        '      <title>Critical Infrastructure Vulnerability Alert</title>\n'
        '      <link>https://www.cisa.gov/advisories/aa26-044a</link>\n'
        '      <pubDate>Thu, 13 Feb 2026</pubDate>\n'
        '      <description><![CDATA[CISA has identified active exploitation of a critical vulnerability.]]></description>\n'
        '    </item>\n'
        '  </channel>\n'
        '</rss>\n'
    )


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