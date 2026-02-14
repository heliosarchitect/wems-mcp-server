"""
Tests for hurricane monitoring functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import httpx

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result, MockResponse


class TestCheckHurricanes:
    """Test hurricane monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_check_hurricanes_default_parameters(self, wems_server_default, mock_hurricane_response, mock_hurricane_alerts_response):
        """Test hurricane checking with default parameters."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "nhc.noaa.gov" in url:
                    return MockResponse(mock_hurricane_response)
                else:  # NWS alerts
                    return MockResponse(mock_hurricane_alerts_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_default._check_hurricanes()
            
            assert_textcontent_result(result)
            assert "Hurricane/Tropical Storm Status" in result[0].text
            assert "Atlantic" in result[0].text  # default basin
            assert "Active Storms" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_hurricanes_premium_all_basins(self, wems_server_premium, mock_hurricane_response, mock_hurricane_alerts_response):
        """Test hurricane checking with all basins (premium)."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "nhc.noaa.gov" in url:
                    return MockResponse(mock_hurricane_response)
                else:  # NWS alerts
                    return MockResponse(mock_hurricane_alerts_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_premium._check_hurricanes(basin="all")
            
            assert_textcontent_result(result)
            assert "All" in result[0].text or "Atlantic" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_hurricanes_free_tier_blocks_pacific(self, wems_server_free):
        """Test that free tier cannot access pacific basin."""
        result = await wems_server_free._check_hurricanes(basin="pacific")
        assert_textcontent_result(result)
        assert "Premium" in result[0].text
        assert "Pacific basin requires" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_hurricanes_free_tier_blocks_forecast(self, wems_server_free):
        """Test that free tier cannot access forecast tracks."""
        result = await wems_server_free._check_hurricanes(include_forecast=True)
        assert_textcontent_result(result)
        assert "Premium" in result[0].text
        assert "Forecast tracks require" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_hurricanes_with_active_storms(self, wems_server_default, mock_hurricane_response_with_storms, mock_hurricane_alerts_response):
        """Test hurricane checking when active storms are present."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "nhc.noaa.gov" in url:
                    return MockResponse(mock_hurricane_response_with_storms)
                elif "api.weather.gov" in url:
                    return MockResponse(mock_hurricane_alerts_response)
                return MockResponse(mock_hurricane_alerts_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_default._check_hurricanes()
            
            assert_textcontent_result(result)
            assert "Active Storms" in result[0].text
            assert "Tropical Storm Alpha" in result[0].text
            assert "Hurricane Beta" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_hurricanes_no_active_storms(self, wems_server_default, mock_hurricane_empty_response, mock_hurricane_alerts_empty_response):
        """Test hurricane checking when no storms are active."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "nhc.noaa.gov" in url:
                    return MockResponse(mock_hurricane_empty_response)
                else:  # NWS alerts
                    return MockResponse(mock_hurricane_alerts_empty_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_default._check_hurricanes()
            
            assert_textcontent_result(result)
            assert "No active hurricanes" in result[0].text
            assert "No active hurricane or tropical storm alerts" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_hurricanes_with_alerts(self, wems_server_default, mock_hurricane_empty_response, mock_hurricane_alerts_response):
        """Test hurricane checking with active alerts but no storms."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "nhc.noaa.gov" in url:
                    return MockResponse(mock_hurricane_empty_response)
                else:  # NWS alerts
                    return MockResponse(mock_hurricane_alerts_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_default._check_hurricanes()
            
            assert_textcontent_result(result)
            assert "Active Tropical Alerts" in result[0].text
            assert "warnings/watches" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_hurricanes_different_storm_icons(self, wems_server_default, mock_hurricane_alerts_empty_response):
        """Test that different storm types get appropriate handling."""
        storm_rss = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0" xmlns:nhc="https://www.nhc.noaa.gov">\n'
            '  <channel>\n'
            '    <title>NHC Atlantic Tropical Cyclones</title>\n'
            '    <item>\n'
            '      <title>Hurricane Alpha</title>\n'
            '      <nhc:center>25.5N 78.2W</nhc:center>\n'
            '      <nhc:movement>NNW at 15 mph</nhc:movement>\n'
            '      <nhc:wind>120 mph</nhc:wind>\n'
            '      <nhc:pressure>945 mb</nhc:pressure>\n'
            '    </item>\n'
            '    <item>\n'
            '      <title>Tropical Storm Beta</title>\n'
            '      <nhc:center>15.2N 65.1W</nhc:center>\n'
            '      <nhc:movement>W at 10 mph</nhc:movement>\n'
            '      <nhc:wind>55 mph</nhc:wind>\n'
            '      <nhc:pressure>1002 mb</nhc:pressure>\n'
            '    </item>\n'
            '    <item>\n'
            '      <title>Tropical Depression Gamma</title>\n'
            '      <nhc:center>12.8N 55.4W</nhc:center>\n'
            '      <nhc:movement>NW at 8 mph</nhc:movement>\n'
            '      <nhc:wind>35 mph</nhc:wind>\n'
            '      <nhc:pressure>1008 mb</nhc:pressure>\n'
            '    </item>\n'
            '  </channel>\n'
            '</rss>\n'
        )
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "nhc.noaa.gov" in url:
                    return MockResponse(storm_rss)
                elif "api.weather.gov" in url:
                    return MockResponse(mock_hurricane_alerts_empty_response)
                return MockResponse(mock_hurricane_alerts_empty_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_default._check_hurricanes()
            
            assert_textcontent_result(result)
            assert "Hurricane Alpha" in result[0].text
            assert "Tropical Storm Beta" in result[0].text
            assert "Tropical Depression Gamma" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_hurricanes_free_tier_limits_results(self, wems_server_free, mock_hurricane_alerts_empty_response):
        """Test that free tier limits hurricane results to 3."""
        items = []
        for i in range(10):
            items.append(
                f'    <item>\n'
                f'      <title>Storm {i+1}</title>\n'
                f'      <nhc:center>{15+i}.0N {60+i}.0W</nhc:center>\n'
                f'      <nhc:movement>NW at {10+i} mph</nhc:movement>\n'
                f'      <nhc:wind>55 mph</nhc:wind>\n'
                f'      <nhc:pressure>1000 mb</nhc:pressure>\n'
                f'    </item>\n'
            )
        storm_rss = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0" xmlns:nhc="https://www.nhc.noaa.gov">\n'
            '  <channel>\n'
            '    <title>NHC Atlantic Tropical Cyclones</title>\n'
            + ''.join(items) +
            '  </channel>\n'
            '</rss>\n'
        )
        
        with patch.object(wems_server_free.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "nhc.noaa.gov" in url:
                    return MockResponse(storm_rss)
                elif "api.weather.gov" in url:
                    return MockResponse(mock_hurricane_alerts_empty_response)
                return MockResponse(mock_hurricane_alerts_empty_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_free._check_hurricanes()
            
            assert_textcontent_result(result)
            # Free tier: max 3 results shown
            storm_count = result[0].text.count("**Storm")  # Count storm names specifically
            assert storm_count == 3
            assert "more storms" in result[0].text  # Should mention remaining results
            assert "Premium" in result[0].text  # Should show upgrade prompt
    
    @pytest.mark.asyncio
    async def test_check_hurricanes_premium_shows_more_results(self, wems_server_premium, mock_hurricane_alerts_empty_response):
        """Test that premium tier shows up to 25 results."""
        items = []
        for i in range(10):
            items.append(
                f'    <item>\n'
                f'      <title>Storm {i+1}</title>\n'
                f'      <nhc:center>{15+i}.0N {60+i}.0W</nhc:center>\n'
                f'      <nhc:movement>NW at {10+i} mph</nhc:movement>\n'
                f'      <nhc:wind>55 mph</nhc:wind>\n'
                f'      <nhc:pressure>1000 mb</nhc:pressure>\n'
                f'    </item>\n'
            )
        storm_rss = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<rss version="2.0" xmlns:nhc="https://www.nhc.noaa.gov">\n'
            '  <channel>\n'
            '    <title>NHC Atlantic Tropical Cyclones</title>\n'
            + ''.join(items) +
            '  </channel>\n'
            '</rss>\n'
        )
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "nhc.noaa.gov" in url:
                    return MockResponse(storm_rss)
                elif "api.weather.gov" in url:
                    return MockResponse(mock_hurricane_alerts_empty_response)
                return MockResponse(mock_hurricane_alerts_empty_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_premium._check_hurricanes()
            
            assert_textcontent_result(result)
            # Premium: all 10 should be shown (limit is 25)
            storm_count = result[0].text.count("**Storm")  # Count storm names specifically
            assert storm_count == 10
    
    @pytest.mark.asyncio
    async def test_check_hurricanes_http_error(self, wems_server_default):
        """Test hurricane checking with HTTP error on all feeds — graceful fallback."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Network error")
            
            result = await wems_server_default._check_hurricanes()
            
            assert_textcontent_result(result)
            # Per-feed and per-alert errors are caught; result shows no storms
            assert "No active hurricanes" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_hurricanes_premium_with_forecast(self, wems_server_premium, mock_hurricane_response, mock_hurricane_alerts_response):
        """Test premium hurricane monitoring with forecast enabled."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            def side_effect(url):
                if "nhc.noaa.gov" in url:
                    return MockResponse(mock_hurricane_response)
                else:  # NWS alerts
                    return MockResponse(mock_hurricane_alerts_response)
            
            mock_get.side_effect = side_effect
            
            result = await wems_server_premium._check_hurricanes(include_forecast=True)
            
            assert_textcontent_result(result)
            assert "Forecast tracks included" in result[0].text


class TestHurricaneAlerts:
    """Test hurricane alert functionality."""
    
    @pytest.mark.asyncio
    async def test_check_hurricane_alert_tropical_storm(self, wems_server):
        """Test hurricane alert for tropical storm intensity."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_hurricane_alert("Alpha", "Tropical Storm", "25.0N 80.0W")
            
            # Should send webhook for tropical storm
            mock_post.assert_called_once()
            
            # Verify webhook payload
            call_args = mock_post.call_args
            assert call_args[1]['json']['event_type'] == 'hurricane'
            assert call_args[1]['json']['storm_name'] == 'Alpha'
            assert call_args[1]['json']['intensity'] == 'Tropical Storm'
            assert call_args[1]['json']['alert_level'] == 'warning'
    
    @pytest.mark.asyncio
    async def test_check_hurricane_alert_hurricane(self, wems_server):
        """Test hurricane alert for hurricane intensity."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_hurricane_alert("Beta", "Category 2 Hurricane", "28.0N 82.0W")
            
            # Should send webhook for hurricane
            mock_post.assert_called_once()
            
            # Verify webhook payload
            call_args = mock_post.call_args
            assert call_args[1]['json']['event_type'] == 'hurricane'
            assert call_args[1]['json']['storm_name'] == 'Beta'
            assert call_args[1]['json']['intensity'] == 'Category 2 Hurricane'
            assert call_args[1]['json']['alert_level'] == 'critical'
    
    @pytest.mark.asyncio
    async def test_check_hurricane_alert_below_threshold(self, wems_server):
        """Test hurricane alert when below notification threshold."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_hurricane_alert("Gamma", "Tropical Depression", "20.0N 70.0W")
            
            # Should not send webhook for tropical depression
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_hurricane_alert_webhook_failure(self, wems_server):
        """Test hurricane alert when webhook fails."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError("Webhook failed")
            
            # Should not raise an exception even if webhook fails
            await wems_server._check_hurricane_alert("Delta", "Hurricane", "30.0N 85.0W")
            
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_hurricane_alert_disabled(self, wems_server_default):
        """Test hurricane alert when alerts are disabled."""
        with patch.object(wems_server_default.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server_default._check_hurricane_alert("Echo", "Hurricane", "32.0N 87.0W")
            
            # Should not send webhook when none configured
            mock_post.assert_not_called()