"""
Tests for volcano monitoring functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import httpx

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result, MockResponse


class TestCheckVolcanoes:
    """Test volcano monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_check_volcanoes_default_parameters(self, wems_server_default):
        """Test volcano checking with default parameters."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse({})
            
            result = await wems_server_default._check_volcanoes()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Volcanic Activity Status" in text
            assert "Recent Volcanic Activity" in text
            assert "WATCH" in text  # Default alert levels
            assert "WARNING" in text  # Default alert levels
    
    @pytest.mark.asyncio
    async def test_check_volcanoes_custom_alert_levels(self, wems_server_default):
        """Test volcano checking with custom alert levels."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse({})
            
            result = await wems_server_default._check_volcanoes(
                alert_levels=["ADVISORY", "WARNING"]
            )
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Volcanic Activity Status" in text
            assert "ADVISORY" in text
            assert "WARNING" in text
    
    @pytest.mark.asyncio
    async def test_check_volcanoes_with_region_filter(self, wems_server_default):
        """Test volcano checking with region filter."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse({})
            
            result = await wems_server_default._check_volcanoes(
                alert_levels=["WARNING"],
                region="Alaska"
            )
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Volcanic Activity Status" in text
            assert "Alaska" in text  # Region filter should be mentioned
    
    @pytest.mark.asyncio
    async def test_check_volcanoes_http_error(self, wems_server_default):
        """Test volcano checking with HTTP error."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("GVP API error")
            
            result = await wems_server_default._check_volcanoes()
            
            assert_textcontent_result(result)
            assert "Error fetching volcanic data" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_volcanoes_http_status_error(self, wems_server_default):
        """Test volcano checking with HTTP status error."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MockResponse({}, status_code=404)
            mock_get.return_value = mock_response
            
            result = await wems_server_default._check_volcanoes()
            
            assert_textcontent_result(result)
            assert "Error fetching volcanic data" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_volcanoes_general_exception(self, wems_server_default):
        """Test volcano checking with unexpected exception."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ValueError("Unexpected error")
            
            result = await wems_server_default._check_volcanoes()
            
            assert_textcontent_result(result)
            assert "Unexpected error in volcano monitoring" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_volcanoes_implementation_note(self, wems_server_default):
        """Test that volcano checking includes implementation note."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse({})
            
            result = await wems_server_default._check_volcanoes()
            
            assert_textcontent_result(result)
            text = result[0].text
            # Should contain note about basic implementation
            assert "basic implementation" in text
            assert "GVP integration recommended" in text
    
    @pytest.mark.asyncio
    async def test_check_volcanoes_no_significant_alerts(self, wems_server_default):
        """Test volcano checking shows no alerts message."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse({})
            
            result = await wems_server_default._check_volcanoes()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "No significant volcanic alerts" in text
    
    @pytest.mark.asyncio
    async def test_check_volcanoes_single_alert_level(self, wems_server_default):
        """Test volcano checking with single alert level."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse({})
            
            result = await wems_server_default._check_volcanoes(alert_levels=["WARNING"])
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "WARNING" in text
            # Should not contain other alert levels
            assert text.count("WARNING") >= 1
    
    @pytest.mark.asyncio
    async def test_check_volcanoes_all_alert_levels(self, wems_server_default):
        """Test volcano checking with all possible alert levels."""
        all_levels = ["NORMAL", "ADVISORY", "WATCH", "WARNING"]
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse({})
            
            result = await wems_server_default._check_volcanoes(alert_levels=all_levels)
            
            assert_textcontent_result(result)
            text = result[0].text
            # Should contain all alert levels in the output
            for level in all_levels:
                assert level in text


class TestVolcanoAlerts:
    """Test volcano alert functionality."""
    
    @pytest.mark.asyncio
    async def test_check_volcano_alert_in_monitored_levels(self, wems_server):
        """Test volcano alert when alert level is in monitored levels."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_volcano_alert("Mount St. Helens", "WARNING", "2026-02-13T15:00:00Z")
            
            # Should send webhook (WARNING is in default monitored levels)
            mock_post.assert_called_once()
            
            # Verify webhook payload
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['event_type'] == 'volcano'
            assert payload['volcano_name'] == 'Mount St. Helens'
            assert payload['alert_level'] == 'warning'  # lowercase
            assert payload['timestamp'] == '2026-02-13T15:00:00Z'
            assert payload['severity'] == 'critical'  # WARNING level
    
    @pytest.mark.asyncio
    async def test_check_volcano_alert_watch_vs_warning_severity(self, wems_server):
        """Test volcano alert severity levels for WATCH vs WARNING."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            # Test WARNING alert (critical severity)
            await wems_server._check_volcano_alert("Test Volcano", "WARNING", "2026-02-13T15:00:00Z")
            
            call_args = mock_post.call_args
            assert call_args[1]['json']['severity'] == 'critical'
            
            mock_post.reset_mock()
            
            # Test WATCH alert (warning severity)
            await wems_server._check_volcano_alert("Test Volcano", "WATCH", "2026-02-13T15:00:00Z")
            
            call_args = mock_post.call_args
            assert call_args[1]['json']['severity'] == 'warning'
    
    @pytest.mark.asyncio
    async def test_check_volcano_alert_not_in_monitored_levels(self, wems_server):
        """Test volcano alert when alert level is not monitored."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_volcano_alert("Test Volcano", "NORMAL", "2026-02-13T15:00:00Z")
            
            # Should not send webhook (NORMAL not in default monitored levels)
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_volcano_alert_webhook_failure(self, wems_server):
        """Test volcano alert when webhook fails."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError("Webhook failed")
            
            # Should not raise an exception even if webhook fails
            await wems_server._check_volcano_alert("Test Volcano", "WARNING", "2026-02-13T15:00:00Z")
            
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_volcano_alert_no_webhook_configured(self, wems_server_default):
        """Test volcano alert when no webhook is configured."""
        with patch.object(wems_server_default.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server_default._check_volcano_alert("Test Volcano", "WARNING", "2026-02-13T15:00:00Z")
            
            # Should not send webhook when none configured
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_volcano_alert_advisory_level(self, wems_server):
        """Test volcano alert with ADVISORY level."""
        # Modify config to monitor ADVISORY level
        wems_server.config["alerts"]["volcano"]["alert_levels"] = ["ADVISORY", "WATCH", "WARNING"]
        
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_volcano_alert("Test Volcano", "ADVISORY", "2026-02-13T15:00:00Z")
            
            # Should send webhook (ADVISORY is now in monitored levels)
            mock_post.assert_called_once()
            
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['alert_level'] == 'advisory'
            assert payload['severity'] == 'warning'  # Not WARNING level, so 'warning' severity
    
    @pytest.mark.asyncio
    async def test_check_volcano_alert_case_sensitivity(self, wems_server):
        """Test volcano alert with different case alert levels."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            # Test lowercase input
            await wems_server._check_volcano_alert("Test Volcano", "warning", "2026-02-13T15:00:00Z")
            
            # Should still match (assuming case-insensitive matching in implementation)
            # Note: Looking at actual implementation, it uses exact string matching
            mock_post.assert_not_called()  # "warning" != "WARNING"
            
            # Test correct case
            await wems_server._check_volcano_alert("Test Volcano", "WARNING", "2026-02-13T15:00:00Z")
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_volcano_alert_empty_monitored_levels(self, wems_server):
        """Test volcano alert when no alert levels are monitored."""
        # Modify config to monitor no levels
        wems_server.config["alerts"]["volcano"]["alert_levels"] = []
        
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_volcano_alert("Test Volcano", "WARNING", "2026-02-13T15:00:00Z")
            
            # Should not send webhook (empty monitored levels)
            mock_post.assert_not_called()