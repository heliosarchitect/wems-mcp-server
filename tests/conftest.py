"""
Test fixtures and configuration for WEMS MCP Server tests.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
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
            "begin_time": (now.replace(hour=now.hour-2)).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "type": "Solar Flare",
            "message": "M2.1 Solar Flare observed from Region 3234",
            "space_weather_message_code": "ALTK05",
            "issue_datetime": now.strftime('%Y-%m-%dT%H:%M:%SZ')
        },
        {
            "begin_time": (now.replace(hour=now.hour-6)).strftime('%Y-%m-%dT%H:%M:%SZ'),
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
            "time": (now.replace(hour=now.hour-3)).isoformat().replace('+00:00', 'Z'),
            "updated": now.isoformat().replace('+00:00', 'Z'),
            "url": "https://www.tsunami.gov/events/PHEB/2024/02/13/PHEB240213.001.html",
            "status": "active"
        }
    ]


@pytest.fixture 
def mock_tsunami_empty_response():
    """Mock empty NOAA tsunami API response."""
    return []


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
    """Create a WEMS server instance for testing."""
    server = WemsServer(temp_config_file)
    yield server
    await server.http_client.aclose()


@pytest.fixture 
async def wems_server_default():
    """Create a WEMS server instance with default config."""
    server = WemsServer()  # No config file - uses defaults
    yield server
    await server.http_client.aclose()


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