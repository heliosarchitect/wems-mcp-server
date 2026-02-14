"""
Tests for space weather alerts functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta
import httpx

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result, MockResponse


class TestCheckSpaceWeatherAlerts:
    """Test space weather alerts functionality."""
    
    @pytest.fixture
    def mock_alerts_response(self):
        """Mock space weather alerts API response."""
        now = datetime.now(timezone.utc)
        return [
            {
                "product_id": "A20F",
                "issue_datetime": (now - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "Space Weather Message Code: WATA20\r\nSerial Number: 1096\r\nIssue Time: 2026 Feb 13 1822 UTC\r\n\r\nWATCH: Geomagnetic Storm Category G1 Predicted\r\n\r\nHighest Storm Level Predicted by Day:\r\nFeb 14:  None (Below G1)   Feb 15:  G1 (Minor)   Feb 16:  G1 (Minor)\r\n\r\nNOAA Scale: G1 - Minor\r\n\r\nPotential Impacts: Area of impact primarily poleward of 60 degrees Geomagnetic Latitude."
            },
            {
                "product_id": "K04A",
                "issue_datetime": (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "Space Weather Message Code: ALTK04\r\nSerial Number: 2631\r\nIssue Time: 2026 Feb 13 0213 UTC\r\n\r\nALERT: Geomagnetic K-index of 4\r\n Threshold Reached: 2026 Feb 13 0213 UTC\r\nSynoptic Period: 0000-0300 UTC\r\n\r\nNOAA Scale: G1 - Minor"
            },
            {
                "product_id": "P11A", 
                "issue_datetime": (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "Space Weather Message Code: ALTPX1\r\nSerial Number: 362\r\nIssue Time: 2026 Jan 18 2311 UTC\r\n\r\nALERT: Proton Event 10MeV Integral Flux exceeded 10pfu\r\nBegin Time: 2026 Jan 18 2255 UTC\r\nNOAA Scale: S1 - Minor\r\n\r\nPotential Impacts: Radio - Minor impacts on polar HF (high frequency) radio propagation resulting in fades at lower frequencies."
            }
        ]
    
    @pytest.mark.asyncio
    async def test_check_space_weather_alerts_default(self, wems_server_default, mock_alerts_response):
        """Test space weather alerts with default parameters."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_alerts_response)
            
            result = await wems_server_default._check_space_weather_alerts()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Active Space Weather Alerts" in text
            assert "Geomagnetic" in text
            assert "G1 - Minor" in text
    
    @pytest.mark.asyncio
    async def test_check_space_weather_alerts_free_tier_limits(self, wems_server_free, mock_alerts_response):
        """Test that free tier limits alerts to 5 and hours to 24."""
        # Add more alerts to test the limit
        now = datetime.now(timezone.utc)
        extended_alerts = mock_alerts_response + [
            {
                "product_id": f"TEST{i}",
                "issue_datetime": (now - timedelta(hours=i+4)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": f"Test alert {i}"
            } for i in range(4, 10)  # Add 6 more alerts
        ]
        
        with patch.object(wems_server_free.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(extended_alerts)
            
            result = await wems_server_free._check_space_weather_alerts()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Active Space Weather Alerts" in text
            # Should show upgrade message due to free tier limits
            assert "Premium" in text or "more alerts" in text
    
    @pytest.mark.asyncio
    async def test_check_space_weather_alerts_premium_shows_all(self, wems_server_premium, mock_alerts_response):
        """Test that premium tier shows all alerts."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_alerts_response)
            
            result = await wems_server_premium._check_space_weather_alerts()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Active Space Weather Alerts" in text
            # Should show all 3 alerts without upgrade message
            assert text.count("Alert") >= 2  # At least 2 alerts shown
    
    @pytest.mark.asyncio
    async def test_check_space_weather_alerts_empty_response(self, wems_server_default):
        """Test space weather alerts when no alerts are active."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse([])
            
            result = await wems_server_default._check_space_weather_alerts()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "No active alerts" in text
    
    @pytest.mark.asyncio
    async def test_check_space_weather_alerts_time_filtering(self, wems_server_default):
        """Test that alerts outside time window are filtered out."""
        now = datetime.now(timezone.utc)
        alerts = [
            {
                "product_id": "NEW1",
                "issue_datetime": (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "Recent alert - should appear"
            },
            {
                "product_id": "OLD1", 
                "issue_datetime": (now - timedelta(hours=30)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "Old alert - should not appear"
            }
        ]
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(alerts)
            
            result = await wems_server_default._check_space_weather_alerts(hours_back=24)
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Recent alert" in text
            assert "Old alert" not in text
    
    @pytest.mark.asyncio
    async def test_check_space_weather_alerts_alert_type_icons(self, wems_server_default):
        """Test that different alert types get appropriate icons."""
        now = datetime.now(timezone.utc)
        alerts = [
            {
                "product_id": "GEO1",
                "issue_datetime": now.strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "Geomagnetic Storm alert with K-index"
            },
            {
                "product_id": "RAD1",
                "issue_datetime": now.strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "Proton radiation storm alert"
            },
            {
                "product_id": "RADIO1",
                "issue_datetime": now.strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "Radio blackout communications disruption"
            },
            {
                "product_id": "FLARE1",
                "issue_datetime": now.strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "Solar flare X-ray event detected"
            }
        ]
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(alerts)
            
            result = await wems_server_default._check_space_weather_alerts()
            
            assert_textcontent_result(result)
            text = result[0].text
            # Check that different types of alerts are categorized
            assert "Geomagnetic" in text
            assert "Radiation" in text
            assert "Radio" in text
            assert "Solar Flare" in text
    
    @pytest.mark.asyncio
    async def test_check_space_weather_alerts_custom_hours_back(self, wems_server_premium):
        """Test custom hours_back parameter."""
        now = datetime.now(timezone.utc)
        alerts = [
            {
                "product_id": "TEST1",
                "issue_datetime": (now - timedelta(hours=10)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "10 hour old alert"
            }
        ]
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(alerts)
            
            # Test with 8 hours - should not show alert
            result = await wems_server_premium._check_space_weather_alerts(hours_back=8)
            assert "No alerts in the last 8 hours" in result[0].text
            
            # Test with 12 hours - should show alert
            result = await wems_server_premium._check_space_weather_alerts(hours_back=12)
            assert "10 hour old alert" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_space_weather_alerts_free_tier_hours_limit(self, wems_server_free):
        """Test that free tier enforces hours_back limit."""
        with patch.object(wems_server_free.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse([])
            
            result = await wems_server_free._check_space_weather_alerts(hours_back=168)  # 7 days
            
            assert_textcontent_result(result)
            text = result[0].text
            # Should show free tier note about time limit
            assert "Free tier" in text and "premium" in text
    
    @pytest.mark.asyncio
    async def test_check_space_weather_alerts_http_error(self, wems_server_default):
        """Test space weather alerts when API fails."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("API failed")
            
            result = await wems_server_default._check_space_weather_alerts()
            
            assert_textcontent_result(result)
            assert "Error fetching space weather alerts" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_space_weather_alerts_json_parse_error(self, wems_server_default):
        """Test space weather alerts when JSON parsing fails."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            # Mock response that will cause JSON parsing to fail
            mock_response = MockResponse("invalid json")
            mock_response.json = lambda: (_ for _ in ()).throw(ValueError("Invalid JSON"))
            mock_get.return_value = mock_response
            
            result = await wems_server_default._check_space_weather_alerts()
            
            assert_textcontent_result(result)
            assert "Unexpected error" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_space_weather_alerts_scale_extraction(self, wems_server_default):
        """Test that NOAA scale information is properly extracted."""
        now = datetime.now(timezone.utc)
        alerts = [
            {
                "product_id": "SCALE1",
                "issue_datetime": now.strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "Alert message\nNOAA Scale: G3 - Strong\nOther info"
            }
        ]
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(alerts)
            
            result = await wems_server_default._check_space_weather_alerts()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "G3 - Strong" in text
    
    @pytest.mark.asyncio
    async def test_check_space_weather_alerts_sorting(self, wems_server_default):
        """Test that alerts are sorted by time (newest first)."""
        now = datetime.now(timezone.utc)
        alerts = [
            {
                "product_id": "OLD",
                "issue_datetime": (now - timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "Older alert"
            },
            {
                "product_id": "NEW",
                "issue_datetime": (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S.%f"),
                "message": "Newer alert"
            }
        ]
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(alerts)
            
            result = await wems_server_default._check_space_weather_alerts()
            
            assert_textcontent_result(result)
            text = result[0].text
            # Newer alert should appear before older alert
            newer_pos = text.find("Newer alert")
            older_pos = text.find("Older alert")
            assert newer_pos < older_pos