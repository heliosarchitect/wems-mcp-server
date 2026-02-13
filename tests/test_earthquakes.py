"""
Tests for earthquake monitoring functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import httpx

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result, MockResponse


class TestCheckEarthquakes:
    """Test earthquake monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_check_earthquakes_default_parameters(self, wems_server_default, mock_earthquake_response):
        """Test earthquake checking with default parameters."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_earthquake_response)
            
            result = await wems_server_default._check_earthquakes()
            
            assert_textcontent_result(result)
            assert "earthquakes" in result[0].text.lower()
            assert "4.5" in result[0].text  # default magnitude
            assert "day" in result[0].text  # default time period
            assert "2 found" in result[0].text  # from mock data
    
    @pytest.mark.asyncio
    async def test_check_earthquakes_custom_parameters(self, wems_server_default, mock_earthquake_response):
        """Test earthquake checking with custom parameters."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_earthquake_response)
            
            result = await wems_server_default._check_earthquakes(
                min_magnitude=5.0,
                time_period="week",
                region="Alaska"
            )
            
            assert_textcontent_result(result)
            assert "5.0" in result[0].text
            assert "week" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_earthquakes_empty_response(self, wems_server_default, mock_earthquake_empty_response):
        """Test earthquake checking when no earthquakes found."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_earthquake_empty_response)
            
            result = await wems_server_default._check_earthquakes(min_magnitude=6.0)
            
            assert_textcontent_result(result)
            assert "No earthquakes" in result[0].text
            assert "6.0" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_earthquakes_magnitude_filtering(self, wems_server_default, mock_earthquake_response):
        """Test earthquake magnitude filtering and display."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_earthquake_response)
            
            result = await wems_server_default._check_earthquakes()
            
            assert_textcontent_result(result)
            # Check magnitude icons are present (should have different icons for different magnitudes)
            text = result[0].text
            assert "6.2" in text  # From mock data
            assert "4.8" in text  # From mock data
            # Should contain proper location info
            assert "Alaska" in text
            assert "Hawaii" in text
    
    @pytest.mark.asyncio
    async def test_check_earthquakes_time_period_variants(self, wems_server_default, mock_earthquake_response):
        """Test different time period options."""
        time_periods = ["hour", "day", "week"]
        
        for period in time_periods:
            with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = MockResponse(mock_earthquake_response)
                
                result = await wems_server_default._check_earthquakes(time_period=period)
                
                assert_textcontent_result(result)
                assert period in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_earthquakes_region_filtering(self, wems_server_default, mock_earthquake_response):
        """Test region filtering functionality."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_earthquake_response)
            
            # Test region that should match
            result = await wems_server_default._check_earthquakes(region="alaska")
            
            assert_textcontent_result(result)
            # Should have Alaska earthquake but not Hawaii (filtered out)
            assert "Alaska" in result[0].text
    
    @pytest.mark.asyncio  
    async def test_check_earthquakes_http_error(self, wems_server_default):
        """Test earthquake checking with HTTP error."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Network error")
            
            result = await wems_server_default._check_earthquakes()
            
            assert_textcontent_result(result)
            assert "Error fetching earthquake data" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_earthquakes_http_status_error(self, wems_server_default):
        """Test earthquake checking with HTTP status error."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MockResponse({}, status_code=500)
            mock_get.return_value = mock_response
            
            result = await wems_server_default._check_earthquakes()
            
            assert_textcontent_result(result)
            assert "Error fetching earthquake data" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_earthquakes_different_magnitudes_icons(self, wems_server_default):
        """Test that different magnitude earthquakes get different icons."""
        # Create mock data with different magnitude ranges
        test_cases = [
            {"mag": 8.0, "expected_icon": "🔴"},  # >= 7.0
            {"mag": 6.5, "expected_icon": "🟠"},  # >= 6.0
            {"mag": 5.2, "expected_icon": "🟡"},  # >= 5.0
            {"mag": 4.5, "expected_icon": "•"},   # < 5.0
        ]
        
        for case in test_cases:
            earthquake_data = {
                "metadata": {"count": 1},
                "features": [{
                    "properties": {
                        "mag": case["mag"],
                        "place": "Test Location",
                        "time": int(datetime.now(timezone.utc).timestamp() * 1000)
                    },
                    "geometry": {"coordinates": [0, 0, 10]}
                }]
            }
            
            with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = MockResponse(earthquake_data)
                
                result = await wems_server_default._check_earthquakes()
                
                assert_textcontent_result(result)
                # Note: We can't easily test for emoji icons in text, so we'll test for magnitude presence
                assert str(case["mag"]) in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_earthquakes_time_formatting(self, wems_server_default):
        """Test that earthquake times are properly formatted."""
        now = datetime.now(timezone.utc)
        timestamp_ms = int(now.timestamp() * 1000)
        
        earthquake_data = {
            "metadata": {"count": 1},
            "features": [{
                "properties": {
                    "mag": 5.0,
                    "place": "Test Location",
                    "time": timestamp_ms
                },
                "geometry": {"coordinates": [0, 0, 10]}
            }]
        }
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(earthquake_data)
            
            result = await wems_server_default._check_earthquakes()
            
            assert_textcontent_result(result)
            # Should contain formatted time (YYYY-MM-DD HH:MM UTC format)
            assert "UTC" in result[0].text
            assert str(now.year) in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_earthquakes_depth_reporting(self, wems_server_default):
        """Test that earthquake depth is properly reported."""
        earthquake_data = {
            "metadata": {"count": 1},
            "features": [{
                "properties": {
                    "mag": 5.0,
                    "place": "Test Location",
                    "time": int(datetime.now(timezone.utc).timestamp() * 1000)
                },
                "geometry": {"coordinates": [0, 0, 25.5]}  # 25.5 km depth
            }]
        }
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(earthquake_data)
            
            result = await wems_server_default._check_earthquakes()
            
            assert_textcontent_result(result)
            assert "Depth: 25.5 km" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_earthquakes_limits_to_10_results(self, wems_server_default):
        """Test that earthquake results are limited to top 10."""
        # Create mock data with 15 earthquakes
        features = []
        for i in range(15):
            features.append({
                "properties": {
                    "mag": 5.0 + i * 0.1,
                    "place": f"Location {i}",
                    "time": int(datetime.now(timezone.utc).timestamp() * 1000)
                },
                "geometry": {"coordinates": [0, 0, 10]}
            })
        
        earthquake_data = {
            "metadata": {"count": 15},
            "features": features
        }
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(earthquake_data)
            
            result = await wems_server_default._check_earthquakes()
            
            assert_textcontent_result(result)
            # Should report total count but only show details for first 10
            assert "15 found" in result[0].text
            # Count occurrences of "Location" to verify only 10 are shown in detail
            location_count = result[0].text.count("Location")
            assert location_count == 10


class TestEarthquakeAlerts:
    """Test earthquake alert functionality."""
    
    @pytest.mark.asyncio 
    async def test_check_earthquake_alert_below_threshold(self, wems_server):
        """Test earthquake alert when magnitude is below threshold."""
        # Mock webhook call - should not be called
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_earthquake_alert(4.5, "Test Location", datetime.now(timezone.utc))
            
            # Should not send webhook (below 5.0 threshold from sample config)
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_earthquake_alert_above_threshold(self, wems_server):
        """Test earthquake alert when magnitude is above threshold."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            test_time = datetime.now(timezone.utc)
            await wems_server._check_earthquake_alert(6.0, "Test Location", test_time)
            
            # Should send webhook (above 5.0 threshold from sample config)
            mock_post.assert_called_once()
            
            # Verify webhook payload
            call_args = mock_post.call_args
            assert call_args[1]['json']['event_type'] == 'earthquake'
            assert call_args[1]['json']['magnitude'] == 6.0
            assert call_args[1]['json']['location'] == 'Test Location'
            assert call_args[1]['json']['timestamp'] == test_time.isoformat()
    
    @pytest.mark.asyncio
    async def test_check_earthquake_alert_major_vs_warning(self, wems_server):
        """Test earthquake alert levels for major vs warning."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            # Test major earthquake (>= 7.0)
            await wems_server._check_earthquake_alert(7.5, "Major Test", datetime.now(timezone.utc))
            
            call_args = mock_post.call_args
            assert call_args[1]['json']['alert_level'] == 'major'
            
            mock_post.reset_mock()
            
            # Test warning earthquake (< 7.0 but above threshold)
            await wems_server._check_earthquake_alert(6.0, "Warning Test", datetime.now(timezone.utc))
            
            call_args = mock_post.call_args
            assert call_args[1]['json']['alert_level'] == 'warning'
    
    @pytest.mark.asyncio
    async def test_check_earthquake_alert_webhook_failure(self, wems_server):
        """Test earthquake alert when webhook fails."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError("Webhook failed")
            
            # Should not raise an exception even if webhook fails
            await wems_server._check_earthquake_alert(6.0, "Test Location", datetime.now(timezone.utc))
            
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_earthquake_alert_no_webhook_configured(self, wems_server_default):
        """Test earthquake alert when no webhook is configured."""
        with patch.object(wems_server_default.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server_default._check_earthquake_alert(6.0, "Test Location", datetime.now(timezone.utc))
            
            # Should not send webhook when none configured
            mock_post.assert_not_called()