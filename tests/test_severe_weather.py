"""
Tests for severe weather monitoring functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import httpx

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result, MockResponse


class TestCheckSevereWeather:
    """Test severe weather monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_default_parameters(self, wems_server_default, mock_severe_weather_response):
        """Test severe weather checking with default parameters."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_severe_weather_response)
            
            result = await wems_server_default._check_severe_weather()
            
            assert_textcontent_result(result)
            assert "Severe Weather Alerts" in result[0].text
            assert "Active Alerts" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_with_state_free_tier_blocked(self, wems_server_default):
        """Test severe weather checking with state filter blocked on free tier."""
        result = await wems_server_default._check_severe_weather(state="TX")
        
        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "State filtering requires WEMS Premium" in result[0].text
        assert "Premium" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_with_state_premium_allowed(self, wems_server_premium, mock_severe_weather_response):
        """Test severe weather checking with state filter on premium tier."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_severe_weather_response)
            
            result = await wems_server_premium._check_severe_weather(state="TX")
            
            assert_textcontent_result(result)
            assert "State: TX" in result[0].text
            assert "🔒" not in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_tornado_warnings(self, wems_server_default, mock_tornado_response):
        """Test severe weather checking with tornado warnings."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_tornado_response)
            
            result = await wems_server_default._check_severe_weather(event_type=["tornado"])
            
            assert_textcontent_result(result)
            assert "🔴🌪️" in result[0].text or "🟠🌪️" in result[0].text
            assert "Tornado" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_thunderstorm_warnings(self, wems_server_default, mock_thunderstorm_response):
        """Test severe weather checking with thunderstorm warnings."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_thunderstorm_response)
            
            result = await wems_server_default._check_severe_weather(event_type=["thunderstorm"])
            
            assert_textcontent_result(result)
            assert "⛈️" in result[0].text
            assert "Thunderstorm" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_flood_warnings(self, wems_server_default, mock_flood_response):
        """Test severe weather checking with flood warnings."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_flood_response)
            
            result = await wems_server_default._check_severe_weather(event_type=["flood"])
            
            assert_textcontent_result(result)
            assert "🌊" in result[0].text
            assert "Flood" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_winter_storm_warnings(self, wems_server_default, mock_winter_storm_response):
        """Test severe weather checking with winter storm warnings."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_winter_storm_response)
            
            result = await wems_server_default._check_severe_weather(event_type=["winter"])
            
            assert_textcontent_result(result)
            assert "❄️" in result[0].text
            assert "Winter" in result[0].text or "Blizzard" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_severity_filtering_free_tier(self, wems_server_default):
        """Test severe weather severity filtering on free tier."""
        result = await wems_server_default._check_severe_weather(severity=["minor", "moderate"])
        
        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "Requested severity levels require WEMS Premium" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_severity_filtering_premium_tier(self, wems_server_premium, mock_severe_weather_all_severities):
        """Test severe weather severity filtering on premium tier."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_severe_weather_all_severities)
            
            result = await wems_server_premium._check_severe_weather(severity=["minor", "moderate", "severe", "extreme"])
            
            assert_textcontent_result(result)
            assert "🔒" not in result[0].text
            assert "Active Alerts" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_no_alerts(self, wems_server_default, mock_empty_alerts_response):
        """Test severe weather checking with no active alerts."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_empty_alerts_response)
            
            result = await wems_server_default._check_severe_weather()
            
            assert_textcontent_result(result)
            assert "🟢 No severe weather alerts" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_urgency_filtering(self, wems_server_premium, mock_urgent_alerts_response):
        """Test severe weather checking with urgency filtering."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_urgent_alerts_response)
            
            result = await wems_server_premium._check_severe_weather(urgency=["immediate", "expected"])
            
            assert_textcontent_result(result)
            assert "Active Alerts" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_certainty_filtering(self, wems_server_premium, mock_certain_alerts_response):
        """Test severe weather checking with certainty filtering."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_certain_alerts_response)
            
            result = await wems_server_premium._check_severe_weather(certainty=["observed", "likely"])
            
            assert_textcontent_result(result)
            assert "Active Alerts" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_free_tier_result_limit(self, wems_server_default, mock_many_alerts_response):
        """Test severe weather checking with result limits on free tier."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_many_alerts_response)
            
            result = await wems_server_default._check_severe_weather()
            
            assert_textcontent_result(result)
            assert "... and" in result[0].text
            assert "Premium" in result[0].text
            assert "Free tier: Last 24h" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_premium_tier_extended_results(self, wems_server_premium, mock_many_alerts_response):
        """Test severe weather checking with extended results on premium tier."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_many_alerts_response)
            
            result = await wems_server_premium._check_severe_weather()
            
            assert_textcontent_result(result)
            assert "UPGRADE" not in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_http_error(self, wems_server_default):
        """Test severe weather checking with HTTP error."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Network error")
            
            result = await wems_server_default._check_severe_weather()
            
            assert_textcontent_result(result)
            assert "❌ Error fetching severe weather data" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_filters_test_messages(self, wems_server_default, mock_test_alerts_response):
        """Test severe weather checking filters out test messages."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_test_alerts_response)
            
            result = await wems_server_default._check_severe_weather()
            
            assert_textcontent_result(result)
            assert "Test Message" not in result[0].text or "🟢 No severe weather alerts" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_severe_weather_time_filtering(self, wems_server_default, mock_old_alerts_response):
        """Test severe weather checking filters alerts by time range."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_old_alerts_response)
            
            result = await wems_server_default._check_severe_weather()
            
            assert_textcontent_result(result)
            # Should show no alerts or very few if they're outside the 24h window
            assert "Data source: National Weather Service" in result[0].text


class TestSevereWeatherAlerts:
    """Test severe weather alert webhook functionality."""
    
    @pytest.mark.asyncio
    async def test_severe_weather_alert_webhook_tornado_warning(self, wems_server_with_alerts):
        """Test tornado warning triggers webhook."""
        with patch.object(wems_server_with_alerts.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MockResponse({})
            
            await wems_server_with_alerts._check_severe_weather_alert(
                "Tornado Warning", "Dallas County, TX", "extreme", "2026-02-13T20:00:00+00:00"
            )
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            assert call_args[1]['json']['event_type'] == 'severe_weather'
            assert call_args[1]['json']['weather_event'] == 'Tornado Warning'
            assert call_args[1]['json']['alert_level'] == 'emergency'
    
    @pytest.mark.asyncio 
    async def test_severe_weather_alert_webhook_extreme_severity(self, wems_server_with_alerts):
        """Test extreme severity alert triggers webhook."""
        with patch.object(wems_server_with_alerts.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MockResponse({})
            
            await wems_server_with_alerts._check_severe_weather_alert(
                "Flash Flood Watch", "Harris County, TX", "extreme", "2026-02-13T20:00:00+00:00"
            )
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            
            assert call_args[1]['json']['alert_level'] == 'critical'
            assert call_args[1]['json']['severity'] == 'extreme'
    
    @pytest.mark.asyncio
    async def test_severe_weather_alert_webhook_disabled(self, wems_server_default):
        """Test webhook not called when alerts disabled."""
        with patch.object(wems_server_default.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server_default._check_severe_weather_alert(
                "Tornado Warning", "Dallas County, TX", "extreme", "2026-02-13T20:00:00+00:00"
            )
            
            mock_post.assert_not_called()