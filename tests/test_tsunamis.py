"""
Tests for tsunami monitoring functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import httpx

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result, MockResponse


class TestCheckTsunamis:
    """Test tsunami monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_default_parameters(self, wems_server_default, mock_tsunami_response):
        """Test tsunami checking with default parameters."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_tsunami_response)
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Tsunami Alert Status" in text
            assert "Active Tsunami Warnings/Advisories" in text
            assert "pacific" in text.lower()  # Default regions
            assert "atlantic" in text.lower()
            assert "indian" in text.lower()
            assert "mediterranean" in text.lower()
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_custom_regions(self, wems_server_default, mock_tsunami_response):
        """Test tsunami checking with custom regions."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_tsunami_response)
            
            result = await wems_server_default._check_tsunamis(regions=["pacific", "atlantic"])
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Tsunami Alert Status" in text
            assert "pacific" in text.lower()
            assert "atlantic" in text.lower()
            # Should not contain regions not specified
            assert text.lower().count("indian") <= 1  # May appear in other contexts
            assert text.lower().count("mediterranean") <= 1
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_active_warnings(self, wems_server_default, mock_tsunami_response):
        """Test tsunami checking with active warnings."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_tsunami_response)
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Active Tsunami Warnings/Advisories" in text
            assert "Near the coast of Central Peru" in text  # From mock data
            assert "7.2" in text  # Magnitude from mock data
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_no_active_warnings(self, wems_server_default, mock_tsunami_empty_response):
        """Test tsunami checking with no active warnings."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_tsunami_empty_response)
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "No active tsunami warnings or advisories" in text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_time_filtering_24h(self, wems_server_default):
        """Test that only warnings from last 24 hours are shown."""
        now = datetime.now(timezone.utc)
        old_time = now.replace(day=now.day-2)  # 2 days ago
        recent_time = now.replace(hour=now.hour-3)  # 3 hours ago
        
        tsunami_data = [
            {
                "location": "Recent Tsunami Location", 
                "magnitude": "6.5",
                "time": recent_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "updated": now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "status": "active"
            },
            {
                "location": "Old Tsunami Location",
                "magnitude": "7.0", 
                "time": old_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "updated": old_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "status": "active"
            }
        ]
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(tsunami_data)
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            text = result[0].text
            # Should contain recent event but not old event
            assert "Recent Tsunami Location" in text
            assert "Old Tsunami Location" not in text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_limits_to_5_warnings(self, wems_server_default):
        """Test that tsunami warnings are limited to 5 most recent."""
        now = datetime.now(timezone.utc)
        tsunami_data = []
        
        # Create 7 recent warnings
        for i in range(7):
            event_time = now.replace(hour=now.hour-i) if now.hour >= i else now.replace(day=now.day-1, hour=24+now.hour-i)
            tsunami_data.append({
                "location": f"Tsunami Location {i}",
                "magnitude": f"{6.0 + i * 0.1}",
                "time": event_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "updated": now.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "status": "active"
            })
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(tsunami_data)
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            text = result[0].text
            
            # Should contain first 5 warnings (most recent)
            for i in range(5):
                assert f"Tsunami Location {i}" in text
            
            # Should not contain the last 2 warnings
            for i in range(5, 7):
                assert f"Tsunami Location {i}" not in text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_time_formatting(self, wems_server_default):
        """Test that tsunami warning times are properly formatted."""
        now = datetime.now(timezone.utc)
        tsunami_data = [{
            "location": "Test Tsunami Location",
            "magnitude": "6.8",
            "time": now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "updated": now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "status": "active"
        }]
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(tsunami_data)
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            text = result[0].text
            # Should contain formatted time (MM-DD HH:MM UTC format)
            assert "UTC" in text
            assert str(now.month).zfill(2) in text or str(now.month) in text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_data_source_info(self, wems_server_default, mock_tsunami_response):
        """Test that tsunami checking includes data source information."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_tsunami_response)
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "NOAA Tsunami Warning Centers" in text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_http_error(self, wems_server_default):
        """Test tsunami checking with HTTP error."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("NOAA API error")
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            assert "Error fetching tsunami data" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_http_status_error(self, wems_server_default):
        """Test tsunami checking with HTTP status error."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MockResponse({}, status_code=503)
            mock_get.return_value = mock_response
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            assert "Error fetching tsunami data" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_general_exception(self, wems_server_default):
        """Test tsunami checking with unexpected exception."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ValueError("Unexpected error")
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            assert "Unexpected error in tsunami monitoring" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_invalid_time_format(self, wems_server_default):
        """Test tsunami checking with invalid time format in data."""
        tsunami_data = [{
            "location": "Test Location",
            "magnitude": "6.0",
            "time": "invalid-time-format",
            "updated": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "status": "active"
        }]
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(tsunami_data)
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            # Should not crash, should handle the error gracefully
            text = result[0].text
            assert "Tsunami Alert Status" in text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_single_region(self, wems_server_default, mock_tsunami_response):
        """Test tsunami checking with single region."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_tsunami_response)
            
            result = await wems_server_default._check_tsunamis(regions=["pacific"])
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "pacific" in text.lower()
            # Regions section should only mention pacific
            lines = text.split('\n')
            regions_line = [line for line in lines if "Regions monitored" in line][0]
            assert regions_line.count(',') == 0  # No commas = single region


class TestTsunamiAlerts:
    """Test tsunami alert functionality."""
    
    @pytest.mark.asyncio
    async def test_check_tsunami_alert_enabled(self, wems_server):
        """Test tsunami alert when alerts are enabled."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_tsunami_alert(
                "Near the coast of Japan", 
                "7.5", 
                "2026-02-13T15:00:00Z"
            )
            
            # Should send webhook (enabled in sample config)
            mock_post.assert_called_once()
            
            # Verify webhook payload
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['event_type'] == 'tsunami'
            assert payload['location'] == 'Near the coast of Japan'
            assert payload['magnitude'] == '7.5'
            assert payload['timestamp'] == '2026-02-13T15:00:00Z'
            assert payload['alert_level'] == 'critical'  # All tsunami warnings are critical
    
    @pytest.mark.asyncio
    async def test_check_tsunami_alert_disabled(self, wems_server):
        """Test tsunami alert when alerts are disabled."""
        # Modify config to disable tsunami alerts
        wems_server.config["alerts"]["tsunami"]["enabled"] = False
        
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_tsunami_alert(
                "Test Location", 
                "6.0", 
                "2026-02-13T15:00:00Z"
            )
            
            # Should not send webhook (disabled)
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_tsunami_alert_no_webhook_configured(self, wems_server_default):
        """Test tsunami alert when no webhook is configured."""
        with patch.object(wems_server_default.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server_default._check_tsunami_alert(
                "Test Location",
                "6.0",
                "2026-02-13T15:00:00Z"
            )
            
            # Should not send webhook when none configured
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_tsunami_alert_webhook_failure(self, wems_server):
        """Test tsunami alert when webhook fails."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError("Webhook failed")
            
            # Should not raise an exception even if webhook fails
            await wems_server._check_tsunami_alert(
                "Test Location",
                "6.0", 
                "2026-02-13T15:00:00Z"
            )
            
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_tsunami_alert_all_critical(self, wems_server):
        """Test that all tsunami alerts are marked as critical."""
        test_cases = [
            ("Small tsunami", "5.0"),
            ("Medium tsunami", "6.5"),
            ("Large tsunami", "8.0")
        ]
        
        for location, magnitude in test_cases:
            with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
                await wems_server._check_tsunami_alert(
                    location,
                    magnitude,
                    "2026-02-13T15:00:00Z"
                )
                
                # All should be critical regardless of magnitude
                call_args = mock_post.call_args
                assert call_args[1]['json']['alert_level'] == 'critical'
                
                mock_post.reset_mock()
    
    @pytest.mark.asyncio
    async def test_check_tsunami_alert_string_magnitude(self, wems_server):
        """Test tsunami alert with string magnitude values."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_tsunami_alert(
                "Test Location",
                "Unknown",  # Non-numeric magnitude
                "2026-02-13T15:00:00Z"
            )
            
            # Should still send webhook and handle non-numeric magnitude
            mock_post.assert_called_once()
            
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['magnitude'] == 'Unknown'
    
    @pytest.mark.asyncio
    async def test_check_tsunami_alert_empty_values(self, wems_server):
        """Test tsunami alert with empty/None values."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_tsunami_alert("", "", "")
            
            # Should send webhook even with empty values (if enabled)
            mock_post.assert_called_once()
            
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['location'] == ''
            assert payload['magnitude'] == ''
            assert payload['timestamp'] == ''
    
    @pytest.mark.asyncio
    async def test_check_tsunami_alert_disabled_by_missing_enabled_flag(self, wems_server):
        """Test tsunami alert when enabled flag is missing from config."""
        # Remove the enabled flag entirely
        del wems_server.config["alerts"]["tsunami"]["enabled"]
        
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_tsunami_alert(
                "Test Location",
                "6.0",
                "2026-02-13T15:00:00Z"
            )
            
            # Should still send webhook (defaults to True when missing)
            mock_post.assert_called_once()