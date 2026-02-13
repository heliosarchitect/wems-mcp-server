"""
Tests for wildfire monitoring functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import httpx

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result, MockResponse


class TestCheckWildfires:
    """Test wildfire monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_check_wildfires_default_parameters(self, wems_server_default, mock_wildfire_alerts_response):
        """Test wildfire checking with default parameters."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_wildfire_alerts_response)
            
            result = await wems_server_default._check_wildfires()
            
            assert_textcontent_result(result)
            assert "Wildfire Activity Status" in result[0].text
            assert "Fire Weather Alerts" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_wildfires_free_tier_blocks_region_filter(self, wems_server_free):
        """Test that free tier cannot use region filtering."""
        result = await wems_server_free._check_wildfires(region="california")
        assert_textcontent_result(result)
        assert "Premium" in result[0].text
        assert "Region filtering requires" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_wildfires_premium_region_filter(self, wems_server_premium, mock_wildfire_alerts_response, mock_wildfire_nifc_response):
        """Test premium wildfire monitoring with region filter."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "weather.gov" in url:
                    return MockResponse(mock_wildfire_alerts_response)
                else:  # NIFC
                    return MockResponse(mock_wildfire_nifc_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_premium._check_wildfires(region="California")
            
            assert_textcontent_result(result)
            assert "Region filter: California" in result[0].text
            assert "Active Large Fires" in result[0].text  # Premium gets NIFC data
    
    @pytest.mark.asyncio
    async def test_check_wildfires_with_active_alerts(self, wems_server_default, mock_wildfire_alerts_response_with_alerts):
        """Test wildfire checking when active alerts are present."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_wildfire_alerts_response_with_alerts)
            
            result = await wems_server_default._check_wildfires()
            
            assert_textcontent_result(result)
            assert "Fire Weather Alerts" in result[0].text
            assert "active" in result[0].text
            assert "Red Flag Warning" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_wildfires_no_active_alerts(self, wems_server_default, mock_wildfire_alerts_empty_response):
        """Test wildfire checking when no alerts are active.""" 
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_wildfire_alerts_empty_response)
            
            result = await wems_server_default._check_wildfires()
            
            assert_textcontent_result(result)
            assert "No active fire weather" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_wildfires_severity_filtering(self, wems_server_default, mock_wildfire_alerts_response_with_alerts):
        """Test wildfire severity filtering."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_wildfire_alerts_response_with_alerts)
            
            result = await wems_server_default._check_wildfires(severity="critical")
            
            assert_textcontent_result(result)
            assert "Severity filter: critical" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_wildfires_premium_with_nifc_data(self, wems_server_premium, mock_wildfire_alerts_response, mock_wildfire_nifc_response):
        """Test premium wildfire monitoring includes NIFC fire perimeter data."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "weather.gov" in url:
                    return MockResponse(mock_wildfire_alerts_response)
                else:  # NIFC
                    return MockResponse(mock_wildfire_nifc_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_premium._check_wildfires()
            
            assert_textcontent_result(result)
            assert "Active Large Fires" in result[0].text
            assert "Wildfire Alpha" in result[0].text  # From NIFC mock data
            assert "acres" in result[0].text
            assert "contained" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_wildfires_premium_no_active_fires(self, wems_server_premium, mock_wildfire_alerts_response, mock_wildfire_nifc_empty_response):
        """Test premium wildfire monitoring when no large fires are active."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "weather.gov" in url:
                    return MockResponse(mock_wildfire_alerts_response)
                else:  # NIFC
                    return MockResponse(mock_wildfire_nifc_empty_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_premium._check_wildfires()
            
            assert_textcontent_result(result)
            assert "No large wildfires currently active" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_wildfires_different_alert_icons(self, wems_server_default):
        """Test that different fire weather alert types get appropriate handling."""
        alert_data = {
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
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(alert_data)
            
            result = await wems_server_default._check_wildfires()
            
            assert_textcontent_result(result)
            assert "Red Flag Warning" in result[0].text
            assert "Fire Weather Watch" in result[0].text
            assert "Central Valley" in result[0].text
            assert "Northern Mountains" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_wildfires_free_tier_limits_results(self, wems_server_free):
        """Test that free tier limits wildfire results to 3."""
        # Create mock data with many alerts
        alerts = []
        for i in range(10):
            alerts.append({
                "properties": {
                    "headline": f"Red Flag Warning {i+1}",
                    "areaDesc": f"Area {i+1}, State",
                    "severity": "Extreme"
                }
            })
        
        alert_data = {"features": alerts}
        
        with patch.object(wems_server_free.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(alert_data)
            
            result = await wems_server_free._check_wildfires()
            
            assert_textcontent_result(result)
            # Free tier: max 3 results shown
            alert_count = result[0].text.count("Red Flag Warning")
            assert alert_count == 3
            assert "more alerts" in result[0].text  # Should mention remaining results
            assert "Premium" in result[0].text  # Should show upgrade prompt
    
    @pytest.mark.asyncio
    async def test_check_wildfires_premium_shows_more_results(self, wems_server_premium, mock_wildfire_nifc_empty_response):
        """Test that premium tier shows up to 25 results."""
        # Create mock data with many alerts
        alerts = []
        for i in range(10):
            alerts.append({
                "properties": {
                    "headline": f"Red Flag Warning {i+1}",
                    "areaDesc": f"Area {i+1}, State",
                    "severity": "Extreme"
                }
            })
        
        alert_data = {"features": alerts}
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "weather.gov" in url:
                    return MockResponse(alert_data)
                else:  # NIFC
                    return MockResponse(mock_wildfire_nifc_empty_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_premium._check_wildfires()
            
            assert_textcontent_result(result)
            # Premium: all 10 should be shown (limit is 25)
            alert_count = result[0].text.count("Red Flag Warning")
            assert alert_count == 10
    
    @pytest.mark.asyncio
    async def test_check_wildfires_http_error(self, wems_server_default):
        """Test wildfire checking with HTTP error."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Network error")
            
            result = await wems_server_default._check_wildfires()
            
            assert_textcontent_result(result)
            assert "Error fetching wildfire data" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_wildfires_nifc_error_fallback(self, wems_server_premium, mock_wildfire_alerts_response):
        """Test that premium tier gracefully handles NIFC API errors."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "weather.gov" in url:
                    return MockResponse(mock_wildfire_alerts_response)
                else:  # NIFC fails
                    raise httpx.HTTPError("NIFC API down")
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_premium._check_wildfires()
            
            assert_textcontent_result(result)
            assert "Fire Weather Alerts" in result[0].text
            # Should still work with NWS data even if NIFC fails


class TestWildfireAlerts:
    """Test wildfire alert functionality."""
    
    @pytest.mark.asyncio
    async def test_check_wildfire_alert_red_flag_warning(self, wems_server):
        """Test wildfire alert for red flag warning."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_wildfire_alert("Red Flag Warning issued", "Central Valley, CA", "Extreme")
            
            # Should send webhook for red flag warning
            mock_post.assert_called_once()
            
            # Verify webhook payload
            call_args = mock_post.call_args
            assert call_args[1]['json']['event_type'] == 'wildfire'
            assert call_args[1]['json']['alert_type'] == 'Red Flag Warning issued'
            assert call_args[1]['json']['severity'] == 'Extreme'
            assert call_args[1]['json']['alert_level'] == 'critical'
    
    @pytest.mark.asyncio
    async def test_check_wildfire_alert_severe_weather(self, wems_server):
        """Test wildfire alert for severe fire weather."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_wildfire_alert("Fire Weather Watch", "Northern California", "Severe")
            
            # Should send webhook for severe fire weather
            mock_post.assert_called_once()
            
            # Verify webhook payload
            call_args = mock_post.call_args
            assert call_args[1]['json']['event_type'] == 'wildfire'
            assert call_args[1]['json']['alert_type'] == 'Fire Weather Watch'
            assert call_args[1]['json']['severity'] == 'Severe'
            assert call_args[1]['json']['alert_level'] == 'warning'
    
    @pytest.mark.asyncio
    async def test_check_wildfire_alert_below_threshold(self, wems_server):
        """Test wildfire alert when below notification threshold."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_wildfire_alert("Fire Weather Watch", "Some Area", "Minor")
            
            # Should not send webhook for minor severity
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_wildfire_alert_webhook_failure(self, wems_server):
        """Test wildfire alert when webhook fails."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError("Webhook failed")
            
            # Should not raise an exception even if webhook fails
            await wems_server._check_wildfire_alert("Red Flag Warning", "Test Area", "Extreme")
            
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_wildfire_alert_disabled(self, wems_server_default):
        """Test wildfire alert when alerts are disabled.""" 
        with patch.object(wems_server_default.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server_default._check_wildfire_alert("Red Flag Warning", "Test Area", "Extreme")
            
            # Should not send webhook when none configured
            mock_post.assert_not_called()