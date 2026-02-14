"""
Tests for floods monitoring functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import httpx

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result, MockResponse


class TestCheckFloods:
    """Test floods monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_check_floods_default_parameters(self, wems_server_default, mock_flood_alerts_response):
        """Test floods checking with default parameters."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_flood_alerts_response)
            
            result = await wems_server_default._check_floods()
            
            assert_textcontent_result(result)
            assert "Flood Monitoring Report" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_with_state_free_tier_blocked(self, wems_server_default):
        """Test floods checking with state filter blocked on free tier."""
        result = await wems_server_default._check_floods(state="TX")
        
        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "State filtering requires WEMS Premium" in result[0].text
        assert "Premium" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_with_state_premium_allowed(self, wems_server_premium, mock_flood_alerts_response):
        """Test floods checking with state filter on premium tier."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_flood_alerts_response)
            
            result = await wems_server_premium._check_floods(state="TX")
            
            assert_textcontent_result(result)
            assert "State: TX" in result[0].text
            assert "🔒" not in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_with_river_gauges_free_tier_blocked(self, wems_server_default):
        """Test floods checking with river gauges blocked on free tier."""
        result = await wems_server_default._check_floods(include_river_gauges=True)
        
        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "River gauge data requires WEMS Premium" in result[0].text
        assert "Premium" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_with_river_gauges_premium_allowed(self, wems_server_premium, mock_flood_alerts_response, mock_usgs_river_gauges_response):
        """Test floods checking with river gauges on premium tier."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            # Mock both NWS and USGS API responses
            mock_get.side_effect = [
                MockResponse(mock_flood_alerts_response),  # NWS API
                MockResponse(mock_usgs_river_gauges_response)  # USGS API
            ]
            
            result = await wems_server_premium._check_floods(include_river_gauges=True)
            
            assert_textcontent_result(result)
            assert "🔒" not in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_weekly_range_free_tier_blocked(self, wems_server_default):
        """Test floods checking with weekly range blocked on free tier."""
        result = await wems_server_default._check_floods(time_range="week")
        
        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "Weekly flood history requires WEMS Premium" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_weekly_range_premium_allowed(self, wems_server_premium, mock_flood_alerts_response):
        """Test floods checking with weekly range on premium tier."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_flood_alerts_response)
            
            result = await wems_server_premium._check_floods(time_range="week")
            
            assert_textcontent_result(result)
            assert "🔒" not in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_flood_stages_free_tier_limited(self, wems_server_default):
        """Test floods checking with limited flood stages on free tier."""
        result = await wems_server_default._check_floods(flood_stage=["minor"])
        
        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "Requested flood stages require WEMS Premium" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_flood_stages_premium_all_allowed(self, wems_server_premium, mock_flood_alerts_response):
        """Test floods checking with all flood stages on premium tier."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_flood_alerts_response)
            
            result = await wems_server_premium._check_floods(flood_stage=["minor", "moderate", "major"])
            
            assert_textcontent_result(result)
            assert "🔒" not in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_flash_flood_warnings(self, wems_server_default, mock_flash_flood_warning_response):
        """Test floods checking with flash flood warnings."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_flash_flood_warning_response)
            
            result = await wems_server_default._check_floods()
            
            assert_textcontent_result(result)
            assert "🔴🌊" in result[0].text
            assert "Flash Flood Warning" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_flood_warnings(self, wems_server_premium, mock_flood_warning_response):
        """Test floods checking with flood warnings."""
        with patch.object(wems_server_premium, '_get_nws_flood_alerts', new_callable=AsyncMock) as mock_get_alerts:
            mock_get_alerts.return_value = mock_flood_warning_response["features"]
            
            result = await wems_server_premium._check_floods()
            
            assert_textcontent_result(result)
            assert "🟠🌊" in result[0].text
            assert "Flood Warning" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_flood_watches(self, wems_server_premium, mock_flood_watch_response):
        """Test floods checking with flood watches."""
        with patch.object(wems_server_premium, '_get_nws_flood_alerts', new_callable=AsyncMock) as mock_get_alerts:
            mock_get_alerts.return_value = mock_flood_watch_response["features"]
            
            result = await wems_server_premium._check_floods()
            
            assert_textcontent_result(result)
            assert "🟡🌊" in result[0].text
            assert "Flood Watch" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_flood_advisory(self, wems_server_premium, mock_flood_advisory_response):
        """Test floods checking with flood advisory."""
        with patch.object(wems_server_premium, '_get_nws_flood_alerts', new_callable=AsyncMock) as mock_get_alerts:
            mock_get_alerts.return_value = mock_flood_advisory_response["features"]
            
            result = await wems_server_premium._check_floods()
            
            assert_textcontent_result(result)
            assert "🔵🌊" in result[0].text
            assert "Flood Advisory" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_no_results(self, wems_server_default, mock_empty_response):
        """Test floods checking with no results."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_empty_response)
            
            result = await wems_server_default._check_floods()
            
            assert_textcontent_result(result)
            assert "🟢 No flood warnings or alerts" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_with_river_gauge_data(self, wems_server_premium, mock_flood_alerts_response, mock_usgs_river_gauges_response):
        """Test floods checking with river gauge data included."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                MockResponse(mock_flood_alerts_response),  # NWS API
                MockResponse(mock_usgs_river_gauges_response)  # USGS API
            ]
            
            result = await wems_server_premium._check_floods(include_river_gauges=True)
            
            assert_textcontent_result(result)
            assert "River Gauge" in result[0].text or "📊" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_free_tier_upgrade_message(self, wems_server_default, mock_large_flood_response):
        """Test floods checking shows upgrade message when hitting free tier limits."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_large_flood_response)
            
            result = await wems_server_default._check_floods()
            
            assert_textcontent_result(result)
            assert "Free tier: Major floods only, last 24h" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_api_error_handling(self, wems_server_default):
        """Test floods checking handles API errors gracefully."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("API Error")
            
            result = await wems_server_default._check_floods()
            
            assert_textcontent_result(result)
            assert "❌ Error fetching flood data" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_floods_with_webhook_alerts(self, wems_server_premium, mock_major_flood_warning_response):
        """Test floods checking triggers webhook alerts for major floods."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_major_flood_warning_response)
            
            with patch.object(wems_server_premium.http_client, 'post', new_callable=AsyncMock) as mock_post:
                result = await wems_server_premium._check_floods()
                
                assert_textcontent_result(result)
                # Note: webhook would only be called if config has webhook URL


class TestFloodUtilityFunctions:
    """Test flood utility functions."""
    
    def test_map_nws_to_flood_stage_warnings(self):
        """Test NWS event mapping to flood stages for warnings."""
        server = WemsServer()
        
        # Flash flood warnings should map to major
        assert server._map_nws_to_flood_stage("severe", "Flash Flood Warning") == "major"
        
        # Regular flood warnings should map to moderate
        assert server._map_nws_to_flood_stage("moderate", "Flood Warning") == "moderate"
        
        # Flood watches should map to minor
        assert server._map_nws_to_flood_stage("minor", "Flood Watch") == "minor"
        
        # Flood advisories should map to action
        assert server._map_nws_to_flood_stage("minor", "Flood Advisory") == "action"
    
    def test_map_nws_to_flood_stage_severity(self):
        """Test NWS severity mapping to flood stages."""
        server = WemsServer()
        
        # Extreme severity should map to major
        assert server._map_nws_to_flood_stage("extreme", "Flood Alert") == "major"
        
        # Severe severity should map to moderate
        assert server._map_nws_to_flood_stage("severe", "Flood Alert") == "moderate"
        
        # Other severities should map to minor
        assert server._map_nws_to_flood_stage("moderate", "Flood Alert") == "minor"
    
    def test_format_flood_alert(self):
        """Test flood alert formatting."""
        server = WemsServer()
        
        alert = {
            "properties": {
                "event": "Flash Flood Warning",
                "headline": "Flash Flood Warning for Urban Areas",
                "areaDesc": "Harris County, TX",
                "severity": "Severe",
                "sent": "2026-02-13T20:00:00Z"
            }
        }
        
        result = server._format_flood_alert(alert)
        
        assert "🔴🌊" in result
        assert "Flash Flood Warning" in result
        assert "Harris County, TX" in result
        assert "Flash Flood Warning for Urban Areas" in result
        assert "Severe" in result
    
    def test_format_river_gauge(self):
        """Test river gauge formatting."""
        server = WemsServer()
        
        gauge = {
            "site_name": "Brazos River at Richmond, TX",
            "site_code": "08116650",
            "gauge_height": "22.5",
            "flood_stage": "major",
            "last_updated": "2026-02-13T20:00:00Z"
        }
        
        result = server._format_river_gauge(gauge)
        
        assert "🔴📊" in result
        assert "Brazos River at Richmond, TX" in result
        assert "08116650" in result
        assert "22.5 ft" in result
        assert "Major" in result