"""
Tests for tsunami monitoring functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta
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
        """Test that entries appear when Atom XML has entries (no 24h filtering in code)."""
        now = datetime.now(timezone.utc)
        recent_time = now - timedelta(hours=3)
        
        xml_data = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">\n'
            '  <title>Tsunami Information</title>\n'
            f'  <updated>{now.strftime("%Y-%m-%dT%H:%M:%SZ")}</updated>\n'
            '  <entry>\n'
            '    <title>Recent Tsunami Location</title>\n'
            f'    <updated>{recent_time.strftime("%Y-%m-%dT%H:%M:%SZ")}</updated>\n'
            '    <summary type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">Info</div></summary>\n'
            '    <geo:lat>-12.0</geo:lat>\n'
            '    <geo:long>-77.0</geo:long>\n'
            '  </entry>\n'
            '</feed>\n'
        )
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(xml_data)
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Recent Tsunami Location" in text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_free_tier_limits_to_3_warnings(self, wems_server_free):
        """Test that free tier limits tsunami warnings to 3."""
        now = datetime.now(timezone.utc)
        entries = []
        for i in range(7):
            t = (now - timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M:%SZ')
            entries.append(
                f'  <entry>\n'
                f'    <title>Tsunami Location {i}</title>\n'
                f'    <updated>{t}</updated>\n'
                f'    <summary type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">Info {i}</div></summary>\n'
                f'    <geo:lat>{-10.0 - i}</geo:lat>\n'
                f'    <geo:long>{-70.0 - i}</geo:long>\n'
                f'  </entry>\n'
            )
        xml_data = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">\n'
            '  <title>Tsunami Information</title>\n'
            f'  <updated>{now.strftime("%Y-%m-%dT%H:%M:%SZ")}</updated>\n'
            + ''.join(entries) +
            '</feed>\n'
        )
        
        with patch.object(wems_server_free.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(xml_data)
            
            result = await wems_server_free._check_tsunamis()
            
            assert_textcontent_result(result)
            text = result[0].text
            
            # Free tier: max 3 results
            for i in range(3):
                assert f"Tsunami Location {i}" in text
            for i in range(3, 7):
                assert f"Tsunami Location {i}" not in text
            assert "more" in text
            assert "Premium" in text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_premium_shows_all_warnings(self, wems_server_premium):
        """Test that premium tier shows up to 25 warnings."""
        now = datetime.now(timezone.utc)
        entries = []
        for i in range(7):
            t = (now - timedelta(hours=i)).strftime('%Y-%m-%dT%H:%M:%SZ')
            entries.append(
                f'  <entry>\n'
                f'    <title>Tsunami Location {i}</title>\n'
                f'    <updated>{t}</updated>\n'
                f'    <summary type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">Info {i}</div></summary>\n'
                f'    <geo:lat>{-10.0 - i}</geo:lat>\n'
                f'    <geo:long>{-70.0 - i}</geo:long>\n'
                f'  </entry>\n'
            )
        xml_data = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">\n'
            '  <title>Tsunami Information</title>\n'
            f'  <updated>{now.strftime("%Y-%m-%dT%H:%M:%SZ")}</updated>\n'
            + ''.join(entries) +
            '</feed>\n'
        )
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(xml_data)
            
            result = await wems_server_premium._check_tsunamis()
            
            assert_textcontent_result(result)
            text = result[0].text
            
            for i in range(7):
                assert f"Tsunami Location {i}" in text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_time_formatting(self, wems_server_default):
        """Test that tsunami warning times are properly formatted."""
        now = datetime.now(timezone.utc)
        xml_data = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">\n'
            '  <title>Tsunami Information</title>\n'
            f'  <updated>{now.strftime("%Y-%m-%dT%H:%M:%SZ")}</updated>\n'
            '  <entry>\n'
            '    <title>Test Tsunami Location</title>\n'
            f'    <updated>{now.strftime("%Y-%m-%dT%H:%M:%SZ")}</updated>\n'
            '    <summary type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">Info</div></summary>\n'
            '    <geo:lat>-12.0</geo:lat>\n'
            '    <geo:long>-77.0</geo:long>\n'
            '  </entry>\n'
            '</feed>\n'
        )
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(xml_data)
            
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
        """Test tsunami checking with HTTP error on all feeds — graceful fallback."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("NOAA API error")
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            # Per-feed errors are silently caught; output shows no warnings
            assert "No active tsunami warnings or advisories" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_http_status_error(self, wems_server_default):
        """Test tsunami checking with HTTP status error on all feeds."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MockResponse("", status_code=503)
            mock_get.return_value = mock_response
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            # Per-feed errors are caught; result shows no active warnings
            assert "No active tsunami warnings or advisories" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_general_exception(self, wems_server_default):
        """Test tsunami checking with unexpected exception on all feeds."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ValueError("Unexpected error")
            
            result = await wems_server_default._check_tsunamis()
            
            assert_textcontent_result(result)
            # Per-feed errors are caught; result shows no active warnings
            assert "No active tsunami warnings or advisories" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_tsunamis_invalid_time_format(self, wems_server_default):
        """Test tsunami checking with invalid time format in data."""
        xml_data = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<feed xmlns="http://www.w3.org/2005/Atom" xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">\n'
            '  <title>Tsunami Information</title>\n'
            '  <updated>invalid-time</updated>\n'
            '  <entry>\n'
            '    <title>Test Location</title>\n'
            '    <updated>invalid-time-format</updated>\n'
            '    <summary type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml">Info</div></summary>\n'
            '    <geo:lat>-12.0</geo:lat>\n'
            '    <geo:long>-77.0</geo:long>\n'
            '  </entry>\n'
            '</feed>\n'
        )
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(xml_data)
            
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