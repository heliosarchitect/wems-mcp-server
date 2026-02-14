"""
Tests for air quality monitoring functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
import httpx

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result, MockResponse


class TestCheckAirQuality:
    """Test air quality monitoring functionality."""

    @pytest.mark.asyncio
    async def test_check_air_quality_default(self, wems_server_default, mock_air_quality_response):
        """Test air quality check with default parameters."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_response)

            result = await wems_server_default._check_air_quality()

            assert_textcontent_result(result)
            assert "Air Quality Report" in result[0].text
            assert "Country: US" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_zip_code_free_blocked(self, wems_server_default):
        """Test that ZIP code filtering is blocked on free tier."""
        result = await wems_server_default._check_air_quality(zip_code="90210")

        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "City/ZIP code filtering requires WEMS Premium" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_city_free_blocked(self, wems_server_default):
        """Test that city filtering is blocked on free tier."""
        result = await wems_server_default._check_air_quality(city="Los Angeles")

        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "City/ZIP code filtering requires WEMS Premium" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_zip_code_premium_allowed(self, wems_server_premium, mock_air_quality_response):
        """Test that ZIP code filtering works on premium tier."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_response)

            result = await wems_server_premium._check_air_quality(zip_code="90210")

            assert_textcontent_result(result)
            assert "🔒" not in result[0].text
            assert "ZIP: 90210" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_city_premium_allowed(self, wems_server_premium, mock_air_quality_response):
        """Test that city filtering works on premium tier."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_response)

            result = await wems_server_premium._check_air_quality(city="Los Angeles")

            assert_textcontent_result(result)
            assert "🔒" not in result[0].text
            assert "City: Los Angeles" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_country_filter_free_limited(self, wems_server_default):
        """Test that free tier is limited to US only."""
        result = await wems_server_default._check_air_quality(country="DE")

        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "DE" in result[0].text
        assert "Premium" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_country_filter_free_us_allowed(self, wems_server_default, mock_air_quality_response):
        """Test that free tier allows US."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_response)

            result = await wems_server_default._check_air_quality(country="US")

            assert_textcontent_result(result)
            # Should show the report (not a blocking message)
            assert "Air Quality Report" in result[0].text
            assert "requires WEMS Premium" not in result[0].text.split("──")[0]

    @pytest.mark.asyncio
    async def test_check_air_quality_country_filter_premium_global(self, wems_server_premium, mock_air_quality_response):
        """Test that premium tier allows global countries."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_response)

            result = await wems_server_premium._check_air_quality(country="DE")

            assert_textcontent_result(result)
            assert "🔒" not in result[0].text
            assert "Country: DE" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_parameters_free_limited(self, wems_server_default):
        """Test that free tier only allows PM2.5 and O3 parameters."""
        result = await wems_server_default._check_air_quality(parameters=["no2", "so2"])

        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "Requested pollutants require WEMS Premium" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_parameters_free_partial_filter(self, wems_server_default, mock_air_quality_response):
        """Test that free tier filters out blocked parameters but keeps allowed ones."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_response)

            result = await wems_server_default._check_air_quality(parameters=["pm25", "no2"])

            assert_textcontent_result(result)
            # Should not block entirely since pm25 is allowed
            assert "Air Quality Report" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_parameters_premium_all(self, wems_server_premium, mock_air_quality_multi_parameter_response):
        """Test that premium tier allows all parameters."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_multi_parameter_response)

            result = await wems_server_premium._check_air_quality(
                parameters=["pm25", "pm10", "o3", "no2", "so2", "co"]
            )

            assert_textcontent_result(result)
            assert "🔒" not in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_forecast_free_blocked(self, wems_server_default):
        """Test that forecast is blocked on free tier."""
        result = await wems_server_default._check_air_quality(include_forecast=True)

        assert_textcontent_result(result)
        assert "🔒" in result[0].text
        assert "AQI forecasts require WEMS Premium" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_forecast_premium_allowed(self, wems_server_premium, mock_air_quality_response):
        """Test that forecast works on premium tier."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_response)

            result = await wems_server_premium._check_air_quality(include_forecast=True)

            assert_textcontent_result(result)
            assert "🔒" not in result[0].text
            assert "Forecast" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_coordinates_search(
        self, wems_server_default,
        mock_air_quality_locations_response
    ):
        """Test coordinate-based station search."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_locations_response)

            result = await wems_server_default._check_air_quality(
                latitude=37.7749, longitude=-122.4194, radius_km=50
            )

            assert_textcontent_result(result)
            assert "Coordinates: 37.7749, -122.4194" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_no_data(self, wems_server_default, mock_air_quality_empty_response):
        """Test air quality check with no data available."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_empty_response)

            result = await wems_server_default._check_air_quality()

            assert_textcontent_result(result)
            assert "No air quality data available" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_http_error(self, wems_server_default):
        """Test air quality check handles HTTP errors gracefully."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("API Error")

            result = await wems_server_default._check_air_quality()

            assert_textcontent_result(result)
            assert "❌ Error fetching air quality data" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_aqi_categories(self, wems_server_default):
        """Test AQI category icons and labels are correct."""
        server = wems_server_default

        icon, label, level = server._aqi_category(25)
        assert icon == "🟢" and label == "Good" and level == "good"

        icon, label, level = server._aqi_category(75)
        assert icon == "🟡" and label == "Moderate" and level == "moderate"

        icon, label, level = server._aqi_category(125)
        assert icon == "🟠" and label == "Unhealthy for Sensitive Groups" and level == "usg"

        icon, label, level = server._aqi_category(175)
        assert icon == "🔴" and label == "Unhealthy" and level == "unhealthy"

        icon, label, level = server._aqi_category(250)
        assert icon == "🟣" and label == "Very Unhealthy" and level == "very_unhealthy"

        icon, label, level = server._aqi_category(400)
        assert icon == "🟤" and label == "Hazardous" and level == "hazardous"

    @pytest.mark.asyncio
    async def test_check_air_quality_aqi_boundary_values(self, wems_server_default):
        """Test AQI category boundary values (0, 50, 51, 100, etc.)."""
        server = wems_server_default

        # Exact boundaries
        assert server._aqi_category(0)[2] == "good"
        assert server._aqi_category(50)[2] == "good"
        assert server._aqi_category(51)[2] == "moderate"
        assert server._aqi_category(100)[2] == "moderate"
        assert server._aqi_category(101)[2] == "usg"
        assert server._aqi_category(150)[2] == "usg"
        assert server._aqi_category(151)[2] == "unhealthy"
        assert server._aqi_category(200)[2] == "unhealthy"
        assert server._aqi_category(201)[2] == "very_unhealthy"
        assert server._aqi_category(300)[2] == "very_unhealthy"
        assert server._aqi_category(301)[2] == "hazardous"

    @pytest.mark.asyncio
    async def test_check_air_quality_pagination_free(self, wems_server_default, mock_air_quality_many_stations_response):
        """Test free tier pagination limit (max 3 stations)."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_many_stations_response)

            result = await wems_server_default._check_air_quality()

            assert_textcontent_result(result)
            text = result[0].text
            # Should have limited results
            assert "more stations" in text or "Free tier" in text

    @pytest.mark.asyncio
    async def test_check_air_quality_pagination_premium(self, wems_server_premium, mock_air_quality_many_stations_response):
        """Test premium tier shows more results."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_many_stations_response)

            result = await wems_server_premium._check_air_quality()

            assert_textcontent_result(result)
            text = result[0].text
            # Premium should show all 10 stations (limit is 25)
            assert "Free tier" not in text

    @pytest.mark.asyncio
    async def test_check_air_quality_hazardous_aqi(self, wems_server_default, mock_air_quality_hazardous_response):
        """Test hazardous AQI values display correctly."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_hazardous_response)

            result = await wems_server_default._check_air_quality()

            assert_textcontent_result(result)
            assert "🟤" in result[0].text
            assert "Hazardous" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_moderate_aqi(self, wems_server_default, mock_air_quality_response):
        """Test moderate AQI values display correctly."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_response)

            result = await wems_server_default._check_air_quality()

            assert_textcontent_result(result)
            # mock has values 42.3 (Good) and 55.1 (Moderate)
            assert "🟢" in result[0].text or "🟡" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_webhook_alert(self, wems_server_with_alerts, mock_air_quality_hazardous_response):
        """Test that webhook alerts fire for unhealthy+ AQI."""
        with patch.object(wems_server_with_alerts.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_hazardous_response)

            with patch.object(wems_server_with_alerts.http_client, 'post', new_callable=AsyncMock) as mock_post:
                result = await wems_server_with_alerts._check_air_quality()

                assert_textcontent_result(result)
                # Webhook should have been called for hazardous value (350)
                if mock_post.called:
                    call_args = mock_post.call_args
                    payload = call_args.kwargs.get('json', call_args[1].get('json', {})) if call_args.kwargs else {}
                    if payload:
                        assert payload.get("event_type") == "air_quality"

    @pytest.mark.asyncio
    async def test_check_air_quality_webhook_not_fired_for_good(self, wems_server_with_alerts, mock_air_quality_response):
        """Test that webhook alerts do NOT fire for good AQI."""
        # Mock response has values 42.3 and 55.1 — below unhealthy threshold
        with patch.object(wems_server_with_alerts.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_response)

            with patch.object(wems_server_with_alerts.http_client, 'post', new_callable=AsyncMock) as mock_post:
                result = await wems_server_with_alerts._check_air_quality()

                assert_textcontent_result(result)
                # Should NOT have fired webhook for good/moderate values
                mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_air_quality_state_display(self, wems_server_default, mock_air_quality_response):
        """Test that state is displayed in output."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_response)

            result = await wems_server_default._check_air_quality(state="CA")

            assert_textcontent_result(result)
            assert "State: CA" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_data_source(self, wems_server_default, mock_air_quality_response):
        """Test that data source attribution is included."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_response)

            result = await wems_server_default._check_air_quality()

            assert_textcontent_result(result)
            assert "EPA AirNow" in result[0].text

    @pytest.mark.asyncio
    async def test_check_air_quality_free_tier_upgrade_prompt(self, wems_server_default, mock_air_quality_response):
        """Test that free tier shows upgrade prompt."""
        with patch.object(wems_server_default.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_air_quality_response)

            result = await wems_server_default._check_air_quality()

            assert_textcontent_result(result)
            assert "Free tier" in result[0].text
            assert "Premium" in result[0].text


class TestAirQualityAlerts:
    """Test air quality alert webhook functionality."""

    @pytest.mark.asyncio
    async def test_air_quality_alert_hazardous(self, wems_server_with_alerts):
        """Test alert fires for hazardous AQI."""
        with patch.object(wems_server_with_alerts.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server_with_alerts._check_air_quality_alert(
                "Test Station", "PM2.5", 350.0, "Hazardous"
            )

            mock_post.assert_called_once()
            payload = mock_post.call_args.kwargs.get('json') or mock_post.call_args[1].get('json')
            assert payload["event_type"] == "air_quality"
            assert payload["station"] == "Test Station"
            assert payload["value"] == 350.0
            assert payload["alert_level"] == "hazardous"

    @pytest.mark.asyncio
    async def test_air_quality_alert_critical(self, wems_server_with_alerts):
        """Test alert level for very unhealthy AQI."""
        with patch.object(wems_server_with_alerts.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server_with_alerts._check_air_quality_alert(
                "Test Station", "PM2.5", 250.0, "Very Unhealthy"
            )

            mock_post.assert_called_once()
            payload = mock_post.call_args.kwargs.get('json') or mock_post.call_args[1].get('json')
            assert payload["alert_level"] == "critical"

    @pytest.mark.asyncio
    async def test_air_quality_alert_warning(self, wems_server_with_alerts):
        """Test alert level for unhealthy AQI."""
        with patch.object(wems_server_with_alerts.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server_with_alerts._check_air_quality_alert(
                "Test Station", "O₃ (Ozone)", 175.0, "Unhealthy"
            )

            mock_post.assert_called_once()
            payload = mock_post.call_args.kwargs.get('json') or mock_post.call_args[1].get('json')
            assert payload["alert_level"] == "warning"

    @pytest.mark.asyncio
    async def test_air_quality_alert_no_webhook_configured(self, wems_server_default):
        """Test alert does nothing when no webhook is configured."""
        with patch.object(wems_server_default.http_client, 'post', new_callable=AsyncMock) as mock_post:
            await wems_server_default._check_air_quality_alert(
                "Test Station", "PM2.5", 350.0, "Hazardous"
            )

            mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_air_quality_alert_webhook_failure(self, wems_server_with_alerts):
        """Test alert handles webhook failure gracefully."""
        with patch.object(wems_server_with_alerts.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.HTTPError("Webhook failed")

            # Should not raise
            await wems_server_with_alerts._check_air_quality_alert(
                "Test Station", "PM2.5", 350.0, "Hazardous"
            )


class TestAirQualityUtility:
    """Test air quality utility methods."""

    def test_openaq_params_mapping(self):
        """Test OpenAQ parameter name to ID mapping."""
        assert WemsServer._OPENAQ_PARAMS["pm25"] == 2
        assert WemsServer._OPENAQ_PARAMS["pm10"] == 1
        assert WemsServer._OPENAQ_PARAMS["o3"] == 3
        assert WemsServer._OPENAQ_PARAMS["no2"] == 5
        assert WemsServer._OPENAQ_PARAMS["so2"] == 9
        assert WemsServer._OPENAQ_PARAMS["co"] == 7

    def test_openaq_param_display_names(self):
        """Test OpenAQ parameter display names."""
        assert WemsServer._OPENAQ_PARAM_NAMES[2] == "PM2.5"
        assert WemsServer._OPENAQ_PARAM_NAMES[1] == "PM10"
        assert WemsServer._OPENAQ_PARAM_NAMES[3] == "O₃ (Ozone)"
        assert WemsServer._OPENAQ_PARAM_NAMES[5] == "NO₂"
        assert WemsServer._OPENAQ_PARAM_NAMES[9] == "SO₂"
        assert WemsServer._OPENAQ_PARAM_NAMES[7] == "CO"
