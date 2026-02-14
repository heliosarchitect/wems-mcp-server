"""
Tests for threat advisory monitoring functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from datetime import datetime, timezone
import httpx

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result, MockResponse


class _MockXMLResponse:
    """Mock HTTP response that returns raw XML text (not JSON)."""

    def __init__(self, text: str, status_code: int = 200):
        self._text = text
        self.status_code = status_code
        self.headers = {"content-type": "application/xml"}

    @property
    def text(self):
        return self._text

    def json(self):
        raise ValueError("Response is XML, not JSON")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                message=f"HTTP {self.status_code}",
                request=MagicMock(),
                response=self,
            )


class TestCheckThreatAdvisories:
    """Test threat advisory monitoring functionality."""

    # ── Default / basic ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_default(
        self, wems_server_default, mock_dhs_ntas_response
    ):
        """Test threat advisories with default parameters (free tier, terrorism only)."""
        with patch.object(
            wems_server_default.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = _MockXMLResponse(mock_dhs_ntas_response)

            result = await wems_server_default._check_threat_advisories()

            assert_textcontent_result(result)
            assert "Threat Advisory Report" in result[0].text
            assert "DHS NTAS" in result[0].text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_no_data(
        self, wems_server_default, mock_threat_advisories_empty_response
    ):
        """Test threat advisories with no active threats."""
        with patch.object(
            wems_server_default.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = _MockXMLResponse(
                mock_threat_advisories_empty_response
            )

            result = await wems_server_default._check_threat_advisories()

            assert_textcontent_result(result)
            assert "No active threat advisories" in result[0].text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_elevated(
        self, wems_server_default, mock_elevated_threat_response
    ):
        """Test threat advisories with elevated threat level."""
        with patch.object(
            wems_server_default.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = _MockXMLResponse(mock_elevated_threat_response)

            result = await wems_server_default._check_threat_advisories()

            assert_textcontent_result(result)
            text = result[0].text
            assert "Elevated" in text
            assert "🟡" in text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_imminent(
        self, wems_server_default, mock_dhs_ntas_imminent_response
    ):
        """Test threat advisories with imminent threat level."""
        with patch.object(
            wems_server_default.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = _MockXMLResponse(mock_dhs_ntas_imminent_response)

            result = await wems_server_default._check_threat_advisories()

            assert_textcontent_result(result)
            text = result[0].text
            assert "Imminent" in text
            assert "🔴" in text

    # ── Tier gating: country filtering ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_countries_free_blocked(
        self, wems_server_default
    ):
        """Test that country filtering is blocked on free tier."""
        result = await wems_server_default._check_threat_advisories(
            countries=["AF", "IQ"]
        )

        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "Country filtering requires WEMS Premium" in result[0].text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_countries_premium_allowed(
        self,
        wems_server_premium,
        mock_dhs_ntas_response,
        mock_state_dept_travel_response,
    ):
        """Test that country filtering works on premium tier."""
        call_count = 0

        async def _mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "dhs.gov" in url:
                return _MockXMLResponse(mock_dhs_ntas_response)
            elif "travel.state.gov" in url:
                return _MockXMLResponse(mock_state_dept_travel_response)
            elif "cisa.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><rss><channel></channel></rss>'
                )
            return _MockXMLResponse('<?xml version="1.0"?><alerts></alerts>')

        with patch.object(
            wems_server_premium.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = _mock_get

            result = await wems_server_premium._check_threat_advisories(
                threat_types=["travel"], countries=["AF"]
            )

            assert_textcontent_result(result)
            assert "🔒" not in result[0].text
            assert "Afghanistan" in result[0].text

    # ── Tier gating: threat types ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_threat_types_free_limited(
        self, wems_server_default
    ):
        """Test that free tier only allows terrorism threat type."""
        result = await wems_server_default._check_threat_advisories(
            threat_types=["travel"]
        )

        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "Requested threat types require WEMS Premium" in result[0].text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_threat_types_free_all_blocked(
        self, wems_server_default
    ):
        """Test that free tier blocks 'all' threat type."""
        result = await wems_server_default._check_threat_advisories(
            threat_types=["all"]
        )

        assert_textcontent_result(result)
        assert "🔒" in result[0].text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_threat_types_premium_all(
        self,
        wems_server_premium,
        mock_dhs_ntas_response,
        mock_state_dept_travel_response,
        mock_cyber_advisories_response,
    ):
        """Test that premium tier can access all threat types."""

        async def _mock_get(url, **kwargs):
            if "dhs.gov" in url:
                return _MockXMLResponse(mock_dhs_ntas_response)
            elif "travel.state.gov" in url:
                return _MockXMLResponse(mock_state_dept_travel_response)
            elif "cisa.gov" in url:
                return _MockXMLResponse(mock_cyber_advisories_response)
            return _MockXMLResponse('<?xml version="1.0"?><alerts></alerts>')

        with patch.object(
            wems_server_premium.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = _mock_get

            result = await wems_server_premium._check_threat_advisories(
                threat_types=["all"]
            )

            assert_textcontent_result(result)
            text = result[0].text
            assert "🔒" not in text
            assert "DHS NTAS" in text
            assert "State Dept" in text
            assert "CISA" in text

    # ── Tier gating: historical / expired ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_historical_free_blocked(
        self, wems_server_default
    ):
        """Test that historical data is blocked on free tier."""
        result = await wems_server_default._check_threat_advisories(
            include_historical=True
        )

        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "Historical threat data requires WEMS Premium" in result[0].text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_expired_free_blocked(
        self, wems_server_default
    ):
        """Test that expired advisories are blocked on free tier."""
        result = await wems_server_default._check_threat_advisories(
            include_expired=True
        )

        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "Expired advisories require WEMS Premium" in result[0].text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_historical_premium_allowed(
        self, wems_server_premium, mock_dhs_ntas_response
    ):
        """Test that premium tier can access historical data."""

        async def _mock_get(url, **kwargs):
            if "dhs.gov" in url:
                return _MockXMLResponse(mock_dhs_ntas_response)
            elif "travel.state.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><rss><channel></channel></rss>'
                )
            elif "cisa.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><rss><channel></channel></rss>'
                )
            return _MockXMLResponse('<?xml version="1.0"?><alerts></alerts>')

        with patch.object(
            wems_server_premium.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = _mock_get

            result = await wems_server_premium._check_threat_advisories(
                include_historical=True
            )

            assert_textcontent_result(result)
            assert "🔒" not in result[0].text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_expired_premium_allowed(
        self, wems_server_premium, mock_dhs_ntas_response
    ):
        """Test that premium tier can access expired advisories."""

        async def _mock_get(url, **kwargs):
            if "dhs.gov" in url:
                return _MockXMLResponse(mock_dhs_ntas_response)
            elif "travel.state.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><rss><channel></channel></rss>'
                )
            elif "cisa.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><rss><channel></channel></rss>'
                )
            return _MockXMLResponse('<?xml version="1.0"?><alerts></alerts>')

        with patch.object(
            wems_server_premium.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = _mock_get

            result = await wems_server_premium._check_threat_advisories(
                include_expired=True
            )

            assert_textcontent_result(result)
            assert "🔒" not in result[0].text

    # ── Threat level filtering ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_threat_levels_filtering(
        self, wems_server_default, mock_dhs_ntas_response
    ):
        """Test filtering by specific threat levels."""
        with patch.object(
            wems_server_default.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = _MockXMLResponse(mock_dhs_ntas_response)

            # Filter for imminent only - our mock has elevated, so no results
            result = await wems_server_default._check_threat_advisories(
                threat_level=["imminent"]
            )

            assert_textcontent_result(result)
            assert "No active threat advisories" in result[0].text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_threat_levels_match(
        self, wems_server_default, mock_elevated_threat_response
    ):
        """Test that threat level filtering includes matching threats."""
        with patch.object(
            wems_server_default.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = _MockXMLResponse(mock_elevated_threat_response)

            result = await wems_server_default._check_threat_advisories(
                threat_level=["elevated"]
            )

            assert_textcontent_result(result)
            text = result[0].text
            assert "Elevated" in text
            assert "Active Advisories" in text

    # ── Region filtering ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_region_free_blocked(
        self, wems_server_default
    ):
        """Test that region filtering is blocked on free tier."""
        result = await wems_server_default._check_threat_advisories(
            region="Middle East"
        )

        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "Region filtering requires WEMS Premium" in result[0].text

    # ── HTTP error handling ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_http_error(self, wems_server_default):
        """Test graceful handling of HTTP errors."""
        with patch.object(
            wems_server_default.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = httpx.HTTPError("Connection timeout")

            result = await wems_server_default._check_threat_advisories()

            assert_textcontent_result(result)
            assert "❌" in result[0].text
            assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_http_status_error(self, wems_server_default):
        """Test graceful handling of HTTP status errors."""
        with patch.object(
            wems_server_default.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_resp = _MockXMLResponse("", status_code=500)
            mock_get.return_value = mock_resp

            result = await wems_server_default._check_threat_advisories()

            assert_textcontent_result(result)
            assert "❌" in result[0].text

    # ── Pagination ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_pagination_free(
        self, wems_server_free, mock_many_travel_advisories_response
    ):
        """Test that free tier is limited to max 3 results."""
        # Free tier is terrorism only, so we test with NTAS containing multiple alerts
        # Build an XML response with 5 alerts
        alerts_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<alerts>\n'
        for i in range(5):
            alerts_xml += (
                f'<alert start="2026/02/{i+1:02d} 00:00" end="2026/08/{i+1:02d} 00:00" '
                f'type="Elevated Threat" link="https://www.dhs.gov/alert{i}">\n'
                f'<summary><![CDATA[Alert number {i+1}]]></summary>\n'
                f'<details><![CDATA[Details for alert {i+1}]]></details>\n'
                f'<locations><location><![CDATA[United States]]></location></locations>\n'
                f'<sectors></sectors>\n'
                f'</alert>\n'
            )
        alerts_xml += '</alerts>\n'

        with patch.object(
            wems_server_free.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = _MockXMLResponse(alerts_xml)

            result = await wems_server_free._check_threat_advisories()

            assert_textcontent_result(result)
            text = result[0].text
            assert "5 found" in text
            # Should show "and X more" upgrade message
            assert "more advisories" in text
            assert "Premium" in text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_pagination_premium(
        self,
        wems_server_premium,
        mock_many_travel_advisories_response,
    ):
        """Test that premium tier can show up to 25 results."""

        async def _mock_get(url, **kwargs):
            if "dhs.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><alerts></alerts>'
                )
            elif "travel.state.gov" in url:
                return _MockXMLResponse(mock_many_travel_advisories_response)
            elif "cisa.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><rss><channel></channel></rss>'
                )
            return _MockXMLResponse('<?xml version="1.0"?><alerts></alerts>')

        with patch.object(
            wems_server_premium.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = _mock_get

            result = await wems_server_premium._check_threat_advisories(
                threat_types=["all"]
            )

            assert_textcontent_result(result)
            text = result[0].text
            # Premium should show all 12 travel advisories (within 25 limit)
            assert "12 found" in text
            # Should NOT show upgrade message
            assert "requires WEMS Premium" not in text.split("───")[0]

    # ── Webhook alert ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_webhook_alert(
        self, wems_server_with_alerts, mock_dhs_ntas_imminent_response
    ):
        """Test that webhook alerts fire for imminent threats."""

        async def _mock_get(url, **kwargs):
            if "dhs.gov" in url:
                return _MockXMLResponse(mock_dhs_ntas_imminent_response)
            elif "travel.state.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><rss><channel></channel></rss>'
                )
            elif "cisa.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><rss><channel></channel></rss>'
                )
            return _MockXMLResponse('<?xml version="1.0"?><alerts></alerts>')

        with patch.object(
            wems_server_with_alerts.http_client, "get", new_callable=AsyncMock
        ) as mock_get, patch.object(
            wems_server_with_alerts.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_get.side_effect = _mock_get
            mock_post.return_value = MockResponse({}, 200)

            result = await wems_server_with_alerts._check_threat_advisories(
                threat_types=["all"]
            )

            assert_textcontent_result(result)
            assert "Imminent" in result[0].text

            # Verify webhook was called
            assert mock_post.called
            call_args = mock_post.call_args
            assert call_args[0][0] == "https://webhook.example.com/threat_advisories"
            payload = call_args[1]["json"]
            assert payload["event_type"] == "threat_advisory"
            assert "imminent" in payload["threat_level"].lower()

    @pytest.mark.asyncio
    async def test_check_threat_advisories_webhook_alert_travel_level4(
        self, wems_server_with_alerts, mock_state_dept_travel_response
    ):
        """Test that webhook alerts fire for Level 4 travel advisories."""

        async def _mock_get(url, **kwargs):
            if "dhs.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><alerts></alerts>'
                )
            elif "travel.state.gov" in url:
                return _MockXMLResponse(mock_state_dept_travel_response)
            elif "cisa.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><rss><channel></channel></rss>'
                )
            return _MockXMLResponse('<?xml version="1.0"?><alerts></alerts>')

        with patch.object(
            wems_server_with_alerts.http_client, "get", new_callable=AsyncMock
        ) as mock_get, patch.object(
            wems_server_with_alerts.http_client, "post", new_callable=AsyncMock
        ) as mock_post:
            mock_get.side_effect = _mock_get
            mock_post.return_value = MockResponse({}, 200)

            result = await wems_server_with_alerts._check_threat_advisories(
                threat_types=["all"]
            )

            assert_textcontent_result(result)
            # Should have fired webhooks for Level 4 advisories
            assert mock_post.called

    # ── Travel advisory specific tests ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_travel_country_filter(
        self, wems_server_premium, mock_state_dept_travel_response
    ):
        """Test filtering travel advisories by specific country."""

        async def _mock_get(url, **kwargs):
            if "dhs.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><alerts></alerts>'
                )
            elif "travel.state.gov" in url:
                return _MockXMLResponse(mock_state_dept_travel_response)
            elif "cisa.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><rss><channel></channel></rss>'
                )
            return _MockXMLResponse('<?xml version="1.0"?><alerts></alerts>')

        with patch.object(
            wems_server_premium.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = _mock_get

            result = await wems_server_premium._check_threat_advisories(
                threat_types=["travel"], countries=["Iraq"]
            )

            assert_textcontent_result(result)
            text = result[0].text
            assert "Iraq" in text
            # Should NOT include Afghanistan (different country)
            assert "Afghanistan" not in text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_travel_level_filter(
        self, wems_server_premium, mock_state_dept_travel_response
    ):
        """Test filtering travel advisories by threat level number."""

        async def _mock_get(url, **kwargs):
            if "dhs.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><alerts></alerts>'
                )
            elif "travel.state.gov" in url:
                return _MockXMLResponse(mock_state_dept_travel_response)
            elif "cisa.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><rss><channel></channel></rss>'
                )
            return _MockXMLResponse('<?xml version="1.0"?><alerts></alerts>')

        with patch.object(
            wems_server_premium.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = _mock_get

            result = await wems_server_premium._check_threat_advisories(
                threat_types=["travel"], threat_level=["4"]
            )

            assert_textcontent_result(result)
            text = result[0].text
            # Should only have Level 4 advisories
            assert "Do Not Travel" in text
            # Level 2 Mexico should be excluded
            assert "Mexico" not in text

    # ── NTAS parsing ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_ntas_with_locations(
        self, wems_server_default, mock_dhs_ntas_response
    ):
        """Test that NTAS advisory locations are displayed."""
        with patch.object(
            wems_server_default.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = _MockXMLResponse(mock_dhs_ntas_response)

            result = await wems_server_default._check_threat_advisories()

            assert_textcontent_result(result)
            text = result[0].text
            assert "United States" in text

    @pytest.mark.asyncio
    async def test_check_threat_advisories_ntas_with_sectors(
        self, wems_server_default, mock_dhs_ntas_response
    ):
        """Test that NTAS advisory sectors are displayed."""
        with patch.object(
            wems_server_default.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = _MockXMLResponse(mock_dhs_ntas_response)

            result = await wems_server_default._check_threat_advisories()

            assert_textcontent_result(result)
            text = result[0].text
            assert "Transportation" in text
            assert "Critical Infrastructure" in text

    # ── Free tier footer ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_free_tier_footer(
        self, wems_server_free, mock_dhs_ntas_response
    ):
        """Test that free tier shows limitation footer."""
        with patch.object(
            wems_server_free.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = _MockXMLResponse(mock_dhs_ntas_response)

            result = await wems_server_free._check_threat_advisories()

            assert_textcontent_result(result)
            text = result[0].text
            assert "Free tier" in text
            assert "US terrorism advisories only" in text

    # ── Cyber advisories ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_cyber_premium(
        self, wems_server_premium, mock_cyber_advisories_response
    ):
        """Test cyber advisories on premium tier."""

        async def _mock_get(url, **kwargs):
            if "dhs.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><alerts></alerts>'
                )
            elif "travel.state.gov" in url:
                return _MockXMLResponse(
                    '<?xml version="1.0"?><rss><channel></channel></rss>'
                )
            elif "cisa.gov" in url:
                return _MockXMLResponse(mock_cyber_advisories_response)
            return _MockXMLResponse('<?xml version="1.0"?><alerts></alerts>')

        with patch.object(
            wems_server_premium.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = _mock_get

            result = await wems_server_premium._check_threat_advisories(
                threat_types=["cyber"]
            )

            assert_textcontent_result(result)
            text = result[0].text
            assert "CISA" in text
            assert "Critical Infrastructure" in text

    # ── Malformed XML ──

    @pytest.mark.asyncio
    async def test_check_threat_advisories_malformed_xml(self, wems_server_default):
        """Test graceful handling of malformed XML responses."""
        with patch.object(
            wems_server_default.http_client, "get", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = _MockXMLResponse("this is not valid xml <><>!!")

            result = await wems_server_default._check_threat_advisories()

            assert_textcontent_result(result)
            # Should not crash — returns "no active advisories"
            assert "No active threat advisories" in result[0].text
