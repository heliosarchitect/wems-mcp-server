"""
Tests for solar/space weather monitoring functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import httpx

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result, MockResponse


class TestCheckSolar:
    """Test solar/space weather monitoring functionality."""
    
    @pytest.mark.asyncio
    async def test_check_solar_default_parameters(self, wems_server_default, mock_solar_kindex_response, mock_solar_events_response):
        """Test solar checking with default parameters."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            # Mock both API calls that _check_solar makes
            mock_get.side_effect = [
                MockResponse(mock_solar_kindex_response),
                MockResponse(mock_solar_events_response)
            ]
            
            result = await wems_server_default._check_solar()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Space Weather Status" in text
            assert "Geomagnetic Activity" in text
            assert "K-index" in text
            assert "Recent Space Weather Events" in text
    
    @pytest.mark.asyncio
    async def test_check_solar_with_event_types(self, wems_server_default, mock_solar_kindex_response, mock_solar_events_response):
        """Test solar checking with specific event types."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                MockResponse(mock_solar_kindex_response),
                MockResponse(mock_solar_events_response)
            ]
            
            result = await wems_server_default._check_solar(event_types=["flare", "cme"])
            
            assert_textcontent_result(result)
            # The current implementation doesn't filter by event_types, but accepts the parameter
            assert "Space Weather Status" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_solar_k_index_levels(self, wems_server_default, mock_solar_events_response):
        """Test different K-index levels and their classifications."""
        test_cases = [
            {"k_index": 8.5, "expected_level": "SEVERE STORM"},
            {"k_index": 6.0, "expected_level": "STRONG STORM"},
            {"k_index": 4.5, "expected_level": "MINOR STORM"},
            {"k_index": 3.2, "expected_level": "UNSETTLED"},
            {"k_index": 1.0, "expected_level": "QUIET"},
        ]
        
        for case in test_cases:
            kindex_data = [{
                "time_tag": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                "k_index": case["k_index"],
                "k_index_flag": "nominal"
            }]
            
            with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.side_effect = [
                    MockResponse(kindex_data),
                    MockResponse(mock_solar_events_response)
                ]
                
                result = await wems_server_default._check_solar()
                
                assert_textcontent_result(result)
                text = result[0].text
                assert case["expected_level"] in text
                assert f"K={case['k_index']}" in text
    
    @pytest.mark.asyncio
    async def test_check_solar_empty_kindex(self, wems_server_default, mock_solar_events_response):
        """Test solar checking when K-index data is empty."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                MockResponse([]),  # Empty K-index data
                MockResponse(mock_solar_events_response)
            ]
            
            result = await wems_server_default._check_solar()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Space Weather Status" in text
            # Should still show events section even without K-index data
            assert "Recent Space Weather Events" in text
    
    @pytest.mark.asyncio
    async def test_check_solar_empty_events(self, wems_server_default, mock_solar_kindex_response):
        """Test solar checking when no recent events."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                MockResponse(mock_solar_kindex_response),
                MockResponse([])  # No events
            ]
            
            result = await wems_server_default._check_solar()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Space Weather Status" in text
            # When events_data is empty list, no events section is added (actual behavior)
            # But the K-index section should still be present
            assert "Geomagnetic Activity" in text
            assert "SEVERE STORM" in text  # From mock data
    
    @pytest.mark.asyncio
    async def test_check_solar_event_filtering_24h(self, wems_server_default, mock_solar_kindex_response):
        """Test that only events from last 24 hours are shown."""
        now = datetime.now(timezone.utc)
        old_time = now.replace(day=now.day-2)  # 2 days ago
        recent_time = now.replace(hour=now.hour-2)  # 2 hours ago
        
        events_data = [
            {
                "begin_time": recent_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "type": "Solar Flare",
                "message": "Recent flare event",
                "space_weather_message_code": "ALTK05"
            },
            {
                "begin_time": old_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
                "type": "Old Event",
                "message": "This should not appear",
                "space_weather_message_code": "OLD01"
            }
        ]
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                MockResponse(mock_solar_kindex_response),
                MockResponse(events_data)
            ]
            
            result = await wems_server_default._check_solar()
            
            assert_textcontent_result(result)
            text = result[0].text
            # Should contain recent event but not old event
            assert "Recent flare event" in text
            assert "This should not appear" not in text
    
    @pytest.mark.asyncio
    async def test_check_solar_event_icons(self, wems_server_premium, mock_solar_kindex_response):
        """Test that different event types get appropriate icons (premium sees all)."""
        events_data = [
            {"type": "Solar Flare", "message": "Flare event", "begin_time": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},
            {"type": "CME", "message": "CME event", "begin_time": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},
            {"type": "Radio Blackout", "message": "Radio event", "begin_time": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},
            {"type": "Other Event", "message": "Other event", "begin_time": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
        ]
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                MockResponse(mock_solar_kindex_response),
                MockResponse(events_data)
            ]
            
            result = await wems_server_premium._check_solar()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Flare event" in text
            assert "CME event" in text
            assert "Radio event" in text
            assert "Other event" in text
    
    @pytest.mark.asyncio
    async def test_check_solar_free_tier_limits_to_3_events(self, wems_server_free, mock_solar_kindex_response):
        """Test that free tier limits recent events to 3."""
        now = datetime.now(timezone.utc)
        events_data = []
        
        for i in range(7):
            event_time = now.replace(hour=now.hour-i) if now.hour >= i else now.replace(day=now.day-1, hour=24+now.hour-i)
            events_data.append({
                "type": f"Event {i}",
                "message": f"Event message {i}",
                "begin_time": event_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            })
        
        with patch.object(wems_server_free.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                MockResponse(mock_solar_kindex_response),
                MockResponse(events_data)
            ]
            
            result = await wems_server_free._check_solar()
            
            assert_textcontent_result(result)
            text = result[0].text
            
            # Free tier: max 3 events shown
            for i in range(3):
                assert f"Event message {i}" in text
            for i in range(3, 7):
                assert f"Event message {i}" not in text
            assert "more" in text
            assert "Premium" in text
    
    @pytest.mark.asyncio
    async def test_check_solar_premium_shows_all_events(self, wems_server_premium, mock_solar_kindex_response):
        """Test that premium tier shows up to 25 events."""
        now = datetime.now(timezone.utc)
        events_data = []
        
        for i in range(7):
            event_time = now.replace(hour=now.hour-i) if now.hour >= i else now.replace(day=now.day-1, hour=24+now.hour-i)
            events_data.append({
                "type": f"Event {i}",
                "message": f"Event message {i}",
                "begin_time": event_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            })
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                MockResponse(mock_solar_kindex_response),
                MockResponse(events_data)
            ]
            
            result = await wems_server_premium._check_solar()
            
            assert_textcontent_result(result)
            text = result[0].text
            
            # Premium: all 7 events should be shown
            for i in range(7):
                assert f"Event message {i}" in text
    
    @pytest.mark.asyncio
    async def test_check_solar_kindex_http_error(self, wems_server_default):
        """Test solar checking when K-index API fails."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("K-index API failed")
            
            result = await wems_server_default._check_solar()
            
            assert_textcontent_result(result)
            assert "Error fetching space weather data" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_solar_events_http_error(self, wems_server_default, mock_solar_kindex_response):
        """Test solar checking when events API fails but K-index succeeds."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                MockResponse(mock_solar_kindex_response),
                httpx.HTTPError("Events API failed")
            ]
            
            result = await wems_server_default._check_solar()
            
            assert_textcontent_result(result)
            assert "Error fetching space weather data" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_solar_general_exception(self, wems_server_default):
        """Test solar checking with unexpected exception."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ValueError("Unexpected error")
            
            result = await wems_server_default._check_solar()
            
            assert_textcontent_result(result)
            assert "Unexpected error in solar monitoring" in result[0].text
    
    @pytest.mark.asyncio
    async def test_check_solar_time_formatting(self, wems_server_default, mock_solar_events_response):
        """Test that times are properly formatted in solar output."""
        now = datetime.now(timezone.utc)
        kindex_data = [{
            "time_tag": now.strftime('%Y-%m-%dT%H:%M:%SZ'),
            "k_index": 5.0,
            "k_index_flag": "nominal"
        }]
        
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [
                MockResponse(kindex_data),
                MockResponse(mock_solar_events_response)
            ]
            
            result = await wems_server_default._check_solar()
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "UTC" in text
            assert str(now.year) in text
            # Time format should be YYYY-MM-DD HH:MM UTC
            assert str(now.month).zfill(2) in text or str(now.month) in text


class TestSolarAlerts:
    """Test solar alert functionality."""
    
    @pytest.mark.asyncio
    async def test_check_solar_alert_below_threshold(self, wems_server):
        """Test solar alert when K-index is below threshold."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server._check_solar_alert(5.0, "STRONG STORM", datetime.now(timezone.utc))
            
            # Should not send webhook (below 6.0 threshold from sample config)
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_solar_alert_above_threshold(self, wems_server):
        """Test solar alert when K-index is above threshold."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            test_time = datetime.now(timezone.utc)
            await wems_server._check_solar_alert(7.5, "SEVERE STORM", test_time)
            
            # Should send webhook (above 6.0 threshold from sample config)
            mock_post.assert_called_once()
            
            # Verify webhook payload
            call_args = mock_post.call_args
            payload = call_args[1]['json']
            assert payload['event_type'] == 'solar'
            assert payload['k_index'] == 7.5
            assert payload['level'] == 'SEVERE STORM'
            assert payload['timestamp'] == test_time.isoformat()
    
    @pytest.mark.asyncio
    async def test_check_solar_alert_severe_vs_warning(self, wems_server):
        """Test solar alert levels for severe vs warning."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            # Test severe alert (>= 8.0)
            await wems_server._check_solar_alert(8.5, "SEVERE STORM", datetime.now(timezone.utc))
            
            call_args = mock_post.call_args
            assert call_args[1]['json']['alert_level'] == 'severe'
            
            mock_post.reset_mock()
            
            # Test warning alert (< 8.0 but above threshold)
            await wems_server._check_solar_alert(7.0, "STRONG STORM", datetime.now(timezone.utc))
            
            call_args = mock_post.call_args
            assert call_args[1]['json']['alert_level'] == 'warning'
    
    @pytest.mark.asyncio
    async def test_check_solar_alert_webhook_failure(self, wems_server):
        """Test solar alert when webhook fails."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError("Webhook failed")
            
            # Should not raise an exception even if webhook fails
            await wems_server._check_solar_alert(7.0, "STRONG STORM", datetime.now(timezone.utc))
            
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_solar_alert_no_webhook_configured(self, wems_server_default):
        """Test solar alert when no webhook is configured."""
        with patch.object(wems_server_default.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server_default._check_solar_alert(7.0, "STRONG STORM", datetime.now(timezone.utc))
            
            # Should not send webhook when none configured
            mock_post.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_solar_alert_exact_threshold(self, wems_server):
        """Test solar alert at exact threshold value."""
        with patch.object(wems_server.http_client, 'post', new_callable=AsyncMock) as mock_post:
            # Test exactly at threshold (6.0 from sample config)
            await wems_server._check_solar_alert(6.0, "STRONG STORM", datetime.now(timezone.utc))
            
            # Should send webhook (>= threshold)
            mock_post.assert_called_once()
            
            call_args = mock_post.call_args
            assert call_args[1]['json']['k_index'] == 6.0