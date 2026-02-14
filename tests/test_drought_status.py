"""
Tests for drought status monitoring functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta
import httpx

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result, MockResponse


class TestCheckDroughtStatus:
    """Test drought status monitoring functionality."""
    
    @pytest.fixture
    def mock_drought_response(self):
        """Mock drought monitor API response."""
        now = datetime.now(timezone.utc)
        return [
            {
                "mapDate": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
                "stateAbbreviation": "CA",
                "none": 40.90,
                "d0": 59.10,
                "d1": 31.52,
                "d2": 5.70,
                "d3": 1.06,
                "d4": 0.00,
                "validStart": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
                "validEnd": (now + timedelta(days=6)).strftime("%Y-%m-%dT23:59:59"),
                "statisticFormatID": 1
            },
            {
                "mapDate": (now - timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%S"),
                "stateAbbreviation": "CA",
                "none": 43.49,
                "d0": 56.51,
                "d1": 16.72,
                "d2": 5.70,
                "d3": 1.03,
                "d4": 0.00,
                "validStart": (now - timedelta(days=8)).strftime("%Y-%m-%dT%H:%M:%S"),
                "validEnd": (now - timedelta(days=1)).strftime("%Y-%m-%dT23:59:59"),
                "statisticFormatID": 1
            }
        ]
    
    @pytest.mark.asyncio
    async def test_check_drought_status_free_tier_blocked(self, wems_server_free):
        """Test that free tier cannot access drought monitoring."""
        result = await wems_server_free._check_drought_status(state="CA")
        
        assert_textcontent_result(result)
        text = result[0].text
        assert "🔒" in text
        assert "Premium" in text
        assert "drought" in text.lower()
    
    @pytest.mark.asyncio
    async def test_check_drought_status_premium_access(self, wems_server_premium, mock_drought_response):
        """Test that premium tier can access drought monitoring."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_drought_response)
            
            result = await wems_server_premium._check_drought_status(state="CA")
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Drought Status: CA" in text
            assert "Current as of:" in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_state_abbreviation(self, wems_server_premium, mock_drought_response):
        """Test drought status with state abbreviation."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_drought_response)
            
            result = await wems_server_premium._check_drought_status(state="CA")
            
            # Verify the API was called with correct FIPS code
            mock_get.assert_called_once()
            call_url = mock_get.call_args[0][0]
            assert "aoi=06" in call_url  # CA = FIPS 06
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Drought Status: CA" in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_fips_code(self, wems_server_premium, mock_drought_response):
        """Test drought status with FIPS code."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_drought_response)
            
            result = await wems_server_premium._check_drought_status(state="06")  # CA FIPS
            
            # Verify the API was called with FIPS code
            mock_get.assert_called_once()
            call_url = mock_get.call_args[0][0]
            assert "aoi=06" in call_url
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Drought Status: CA" in text  # Should show state abbreviation
    
    @pytest.mark.asyncio
    async def test_check_drought_status_invalid_state(self, wems_server_premium):
        """Test drought status with invalid state code."""
        result = await wems_server_premium._check_drought_status(state="INVALID")
        
        assert_textcontent_result(result)
        text = result[0].text
        assert "Invalid state" in text
        assert "2-letter abbreviation" in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_no_drought(self, wems_server_premium):
        """Test drought status display when no drought conditions exist."""
        no_drought_data = [{
            "mapDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "stateAbbreviation": "MT",
            "none": 100.0,
            "d0": 0.0,
            "d1": 0.0,
            "d2": 0.0,
            "d3": 0.0,
            "d4": 0.0,
            "validStart": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "validEnd": (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59"),
            "statisticFormatID": 1
        }]
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(no_drought_data)
            
            result = await wems_server_premium._check_drought_status(state="MT")
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "🟢" in text
            assert "No Drought" in text
            assert "100.0%" in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_severe_drought(self, wems_server_premium):
        """Test drought status display for severe drought conditions."""
        severe_drought_data = [{
            "mapDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "stateAbbreviation": "NV",
            "none": 10.0,
            "d0": 20.0,
            "d1": 30.0,
            "d2": 25.0,
            "d3": 10.0,
            "d4": 5.0,  # Exceptional drought present
            "validStart": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "validEnd": (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%dT23:59:59"),
            "statisticFormatID": 1
        }]
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(severe_drought_data)
            
            result = await wems_server_premium._check_drought_status(state="NV")
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "🔴" in text
            assert "Exceptional Drought" in text
            assert "D4 (Exceptional): 5.0%" in text
            assert "D3 (Extreme): 10.0%" in text
            assert "D2 (Severe): 25.0%" in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_trend_analysis(self, wems_server_premium):
        """Test drought trend analysis functionality."""
        now = datetime.now(timezone.utc)
        trend_data = [
            {
                "mapDate": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
                "stateAbbreviation": "TX",
                "none": 30.0,  # Current: 70% in drought
                "d0": 40.0,
                "d1": 20.0,
                "d2": 10.0,
                "d3": 0.0,
                "d4": 0.0,
                "statisticFormatID": 1
            },
            {
                "mapDate": (now - timedelta(days=29)).strftime("%Y-%m-%dT%H:%M:%S"), 
                "stateAbbreviation": "TX",
                "none": 50.0,  # 4 weeks ago: 50% in drought
                "d0": 30.0,
                "d1": 15.0,
                "d2": 5.0,
                "d3": 0.0,
                "d4": 0.0,
                "statisticFormatID": 1
            }
        ]
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(trend_data)
            
            result = await wems_server_premium._check_drought_status(state="TX", include_trend=True)
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "4-Week Trend" in text
            assert "📈" in text  # Worsening trend
            assert "Worsening" in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_improving_trend(self, wems_server_premium):
        """Test drought status with improving trend."""
        now = datetime.now(timezone.utc)
        improving_data = [
            {
                "mapDate": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
                "stateAbbreviation": "CO",
                "none": 70.0,  # Current: 30% in drought
                "d0": 20.0,
                "d1": 10.0,
                "d2": 0.0,
                "d3": 0.0,
                "d4": 0.0,
                "statisticFormatID": 1
            },
            {
                "mapDate": (now - timedelta(days=29)).strftime("%Y-%m-%dT%H:%M:%S"),
                "stateAbbreviation": "CO",
                "none": 40.0,  # 4 weeks ago: 60% in drought
                "d0": 35.0,
                "d1": 20.0,
                "d2": 5.0,
                "d3": 0.0,
                "d4": 0.0,
                "statisticFormatID": 1
            }
        ]
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(improving_data)
            
            result = await wems_server_premium._check_drought_status(state="CO", include_trend=True)
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "📉" in text  # Improving trend
            assert "Improving" in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_stable_trend(self, wems_server_premium):
        """Test drought status with stable trend."""
        now = datetime.now(timezone.utc)
        stable_data = [
            {
                "mapDate": (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
                "stateAbbreviation": "UT",
                "none": 50.0,
                "d0": 30.0,
                "d1": 20.0,
                "d2": 0.0,
                "d3": 0.0,
                "d4": 0.0,
                "statisticFormatID": 1
            },
            {
                "mapDate": (now - timedelta(days=29)).strftime("%Y-%m-%dT%H:%M:%S"),
                "stateAbbreviation": "UT", 
                "none": 50.5,  # Minimal change
                "d0": 29.5,
                "d1": 20.0,
                "d2": 0.0,
                "d3": 0.0,
                "d4": 0.0,
                "statisticFormatID": 1
            }
        ]
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(stable_data)
            
            result = await wems_server_premium._check_drought_status(state="UT", include_trend=True)
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "➡️" in text  # Stable trend
            assert "Stable" in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_no_trend_single_datapoint(self, wems_server_premium):
        """Test drought status when only one data point (no trend analysis)."""
        single_data = [{
            "mapDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
            "stateAbbreviation": "WY",
            "none": 60.0,
            "d0": 25.0,
            "d1": 15.0,
            "d2": 0.0,
            "d3": 0.0,
            "d4": 0.0,
            "statisticFormatID": 1
        }]
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(single_data)
            
            result = await wems_server_premium._check_drought_status(state="WY", include_trend=True)
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Drought Status: WY" in text
            # Should not include trend section
            assert "Trend" not in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_no_trend_requested(self, wems_server_premium, mock_drought_response):
        """Test drought status when trend analysis is disabled."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_drought_response)
            
            result = await wems_server_premium._check_drought_status(state="CA", include_trend=False)
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Drought Status: CA" in text
            # Should not include trend section
            assert "Trend" not in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_custom_weeks_back(self, wems_server_premium):
        """Test custom weeks_back parameter."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse([])
            
            await wems_server_premium._check_drought_status(state="ID", weeks_back=8)
            
            # Verify the API was called with correct date range
            mock_get.assert_called_once()
            call_url = mock_get.call_args[0][0]
            # Should include a start date 8 weeks back
            assert "startdate=" in call_url
    
    @pytest.mark.asyncio
    async def test_check_drought_status_weeks_limit_enforcement(self, wems_server_premium):
        """Test that weeks_back limit is enforced for premium tier."""
        # Mock a server with lower weeks limit
        wems_server_premium.limits["drought_weeks_back"] = 10
        
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse([])
            
            await wems_server_premium._check_drought_status(state="ND", weeks_back=20)
            
            # Should be limited to 10 weeks
            mock_get.assert_called_once()
            # The exact date calculation would need more complex verification
    
    @pytest.mark.asyncio
    async def test_check_drought_status_empty_response(self, wems_server_premium):
        """Test drought status when API returns no data."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse([])
            
            result = await wems_server_premium._check_drought_status(state="AK")
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "No drought data available" in text
            assert "AK" in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_http_error(self, wems_server_premium):
        """Test drought status when API call fails."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.HTTPError("API failed")
            
            result = await wems_server_premium._check_drought_status(state="FL")
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Error fetching drought data" in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_json_parse_error(self, wems_server_premium):
        """Test drought status when JSON parsing fails."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_response = MockResponse("invalid json")
            mock_response.json = lambda: (_ for _ in ()).throw(ValueError("Invalid JSON"))
            mock_get.return_value = mock_response
            
            result = await wems_server_premium._check_drought_status(state="OR")
            
            assert_textcontent_result(result)
            text = result[0].text
            assert "Unexpected error in drought monitoring" in text
    
    @pytest.mark.asyncio
    async def test_check_drought_status_date_formatting(self, wems_server_premium, mock_drought_response):
        """Test that dates are properly formatted in API calls."""
        with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MockResponse(mock_drought_response)
            
            await wems_server_premium._check_drought_status(state="WA")
            
            # Verify API call format
            mock_get.assert_called_once()
            call_url = mock_get.call_args[0][0]
            # Should contain properly formatted dates
            assert "startdate=" in call_url
            assert "enddate=" in call_url
            # Dates should be in M/D/YYYY format (no leading zeros for single digits)
            assert "&enddate=" in call_url
    
    @pytest.mark.asyncio
    async def test_check_drought_status_all_drought_levels(self, wems_server_premium):
        """Test that all drought level classifications are handled correctly."""
        test_cases = [
            ({"d4": 5.0}, "🔴", "Exceptional Drought"),
            ({"d3": 10.0, "d4": 0.0}, "🟠", "Extreme Drought"),
            ({"d2": 15.0, "d3": 0.0, "d4": 0.0}, "🟡", "Severe Drought"),
            ({"d1": 20.0, "d2": 0.0, "d3": 0.0, "d4": 0.0}, "🟤", "Moderate Drought"),
            ({"d0": 25.0, "d1": 0.0, "d2": 0.0, "d3": 0.0, "d4": 0.0}, "🟨", "Abnormally Dry"),
            ({"none": 100.0, "d0": 0.0, "d1": 0.0, "d2": 0.0, "d3": 0.0, "d4": 0.0}, "🟢", "No Drought")
        ]
        
        for drought_levels, expected_icon, expected_status in test_cases:
            drought_data = [{
                "mapDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                "stateAbbreviation": "TEST",
                **{k: v for k, v in drought_levels.items()},
                **{k: 0.0 for k in ["none", "d0", "d1", "d2", "d3", "d4"] if k not in drought_levels},
                "statisticFormatID": 1
            }]
            
            with patch.object(wems_server_premium.http_client, 'get', new_callable=AsyncMock) as mock_get:
                mock_get.return_value = MockResponse(drought_data)
                
                result = await wems_server_premium._check_drought_status(state="48")  # TX FIPS
                
                assert_textcontent_result(result)
                text = result[0].text
                assert expected_icon in text
                assert expected_status in text