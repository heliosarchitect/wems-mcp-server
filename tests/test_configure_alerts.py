"""
Tests for alert configuration functionality.
"""

import pytest
from unittest.mock import patch, AsyncMock

from wems_mcp_server import WemsServer
from tests.conftest import assert_textcontent_result


class TestConfigureAlerts:
    """Test alert configuration functionality."""
    
    @pytest.mark.asyncio
    async def test_configure_earthquake_alerts(self, wems_server):
        """Test configuring earthquake alert settings."""
        new_config = {
            "min_magnitude": 5.5,
            "webhook": "https://new-webhook.example.com/earthquake"
        }
        
        result = await wems_server._configure_alerts("earthquake", new_config)
        
        assert_textcontent_result(result)
        assert "Updated earthquake alert configuration" in result[0].text
        assert str(new_config) in result[0].text
        
        # Verify configuration was actually updated
        assert wems_server.config["alerts"]["earthquake"]["min_magnitude"] == 5.5
        assert wems_server.config["alerts"]["earthquake"]["webhook"] == "https://new-webhook.example.com/earthquake"
    
    @pytest.mark.asyncio
    async def test_configure_solar_alerts(self, wems_server):
        """Test configuring solar alert settings."""
        new_config = {
            "min_kp_index": 8.0,
            "webhook": "https://new-webhook.example.com/solar",
            "event_types": ["flare", "cme", "geomagnetic"]
        }
        
        result = await wems_server._configure_alerts("solar", new_config)
        
        assert_textcontent_result(result)
        assert "Updated solar alert configuration" in result[0].text
        
        # Verify configuration was actually updated
        assert wems_server.config["alerts"]["solar"]["min_kp_index"] == 8.0
        assert wems_server.config["alerts"]["solar"]["webhook"] == "https://new-webhook.example.com/solar"
        assert wems_server.config["alerts"]["solar"]["event_types"] == ["flare", "cme", "geomagnetic"]
    
    @pytest.mark.asyncio
    async def test_configure_volcano_alerts(self, wems_server):
        """Test configuring volcano alert settings."""
        new_config = {
            "alert_levels": ["ADVISORY", "WATCH", "WARNING"],
            "webhook": "https://new-webhook.example.com/volcano",
            "regions": ["Alaska", "Cascades"]
        }
        
        result = await wems_server._configure_alerts("volcano", new_config)
        
        assert_textcontent_result(result)
        assert "Updated volcano alert configuration" in result[0].text
        
        # Verify configuration was actually updated
        assert wems_server.config["alerts"]["volcano"]["alert_levels"] == ["ADVISORY", "WATCH", "WARNING"]
        assert wems_server.config["alerts"]["volcano"]["webhook"] == "https://new-webhook.example.com/volcano"
        assert wems_server.config["alerts"]["volcano"]["regions"] == ["Alaska", "Cascades"]
    
    @pytest.mark.asyncio
    async def test_configure_tsunami_alerts(self, wems_server):
        """Test configuring tsunami alert settings."""
        new_config = {
            "enabled": False,
            "webhook": None,
            "regions": ["pacific"]
        }
        
        result = await wems_server._configure_alerts("tsunami", new_config)
        
        assert_textcontent_result(result)
        assert "Updated tsunami alert configuration" in result[0].text
        
        # Verify configuration was actually updated
        assert wems_server.config["alerts"]["tsunami"]["enabled"] is False
        assert wems_server.config["alerts"]["tsunami"]["webhook"] is None
        assert wems_server.config["alerts"]["tsunami"]["regions"] == ["pacific"]
    
    @pytest.mark.asyncio
    async def test_configure_alerts_unknown_type(self, wems_server):
        """Test configuring alerts for unknown alert type."""
        result = await wems_server._configure_alerts("unknown_type", {"setting": "value"})
        
        assert_textcontent_result(result)
        assert "Unknown alert type: unknown_type" in result[0].text
        
        # Verify no configuration was changed
        original_config = {
            "earthquake": {"min_magnitude": 5.0, "webhook": "https://webhook.example.com/earthquake"},
            "solar": {"min_kp_index": 6.0, "webhook": "https://webhook.example.com/solar"},
            "volcano": {"alert_levels": ["WARNING", "WATCH"], "webhook": "https://webhook.example.com/volcano"},
            "tsunami": {"enabled": True, "webhook": "https://webhook.example.com/tsunami"}
        }
        
        for alert_type, expected_config in original_config.items():
            for key, value in expected_config.items():
                assert wems_server.config["alerts"][alert_type][key] == value
    
    @pytest.mark.asyncio
    async def test_configure_alerts_partial_update(self, wems_server):
        """Test configuring alerts with partial configuration update."""
        # Only update one setting, others should remain unchanged
        original_webhook = wems_server.config["alerts"]["earthquake"]["webhook"]
        
        new_config = {"min_magnitude": 6.5}  # Only update magnitude
        
        result = await wems_server._configure_alerts("earthquake", new_config)
        
        assert_textcontent_result(result)
        assert "Updated earthquake alert configuration" in result[0].text
        
        # Verify partial update
        assert wems_server.config["alerts"]["earthquake"]["min_magnitude"] == 6.5
        assert wems_server.config["alerts"]["earthquake"]["webhook"] == original_webhook  # Unchanged
    
    @pytest.mark.asyncio
    async def test_configure_alerts_overwrite_existing(self, wems_server):
        """Test configuring alerts overwrites existing values."""
        # Set initial configuration
        wems_server.config["alerts"]["solar"]["min_kp_index"] = 7.0
        wems_server.config["alerts"]["solar"]["custom_setting"] = "initial_value"
        
        new_config = {
            "min_kp_index": 5.0,  # Change existing
            "custom_setting": "new_value",  # Overwrite existing
            "new_setting": "added_value"  # Add new
        }
        
        result = await wems_server._configure_alerts("solar", new_config)
        
        assert_textcontent_result(result)
        assert "Updated solar alert configuration" in result[0].text
        
        # Verify all updates
        assert wems_server.config["alerts"]["solar"]["min_kp_index"] == 5.0
        assert wems_server.config["alerts"]["solar"]["custom_setting"] == "new_value"
        assert wems_server.config["alerts"]["solar"]["new_setting"] == "added_value"
    
    @pytest.mark.asyncio
    async def test_configure_alerts_empty_config(self, wems_server):
        """Test configuring alerts with empty configuration."""
        original_config = wems_server.config["alerts"]["earthquake"].copy()
        
        result = await wems_server._configure_alerts("earthquake", {})
        
        assert_textcontent_result(result)
        assert "Updated earthquake alert configuration" in result[0].text
        assert "{}" in result[0].text  # Empty dict should be shown
        
        # Original configuration should remain unchanged
        assert wems_server.config["alerts"]["earthquake"] == original_config
    
    @pytest.mark.asyncio
    async def test_configure_alerts_none_values(self, wems_server):
        """Test configuring alerts with None values."""
        new_config = {
            "webhook": None,
            "min_magnitude": None,
            "regions": None
        }
        
        result = await wems_server._configure_alerts("earthquake", new_config)
        
        assert_textcontent_result(result)
        assert "Updated earthquake alert configuration" in result[0].text
        
        # Verify None values are set
        assert wems_server.config["alerts"]["earthquake"]["webhook"] is None
        assert wems_server.config["alerts"]["earthquake"]["min_magnitude"] is None
        assert wems_server.config["alerts"]["earthquake"]["regions"] is None
    
    @pytest.mark.asyncio
    async def test_configure_alerts_complex_nested_config(self, wems_server):
        """Test configuring alerts with complex nested configuration."""
        new_config = {
            "thresholds": {
                "low": 4.0,
                "medium": 5.5,
                "high": 7.0
            },
            "webhooks": {
                "primary": "https://primary.example.com",
                "backup": "https://backup.example.com"
            },
            "filters": ["region", "magnitude", "depth"],
            "enabled": True
        }
        
        result = await wems_server._configure_alerts("earthquake", new_config)
        
        assert_textcontent_result(result)
        assert "Updated earthquake alert configuration" in result[0].text
        
        # Verify complex nested structure is preserved
        config = wems_server.config["alerts"]["earthquake"]
        assert config["thresholds"]["low"] == 4.0
        assert config["thresholds"]["medium"] == 5.5
        assert config["thresholds"]["high"] == 7.0
        assert config["webhooks"]["primary"] == "https://primary.example.com"
        assert config["webhooks"]["backup"] == "https://backup.example.com"
        assert config["filters"] == ["region", "magnitude", "depth"]
        assert config["enabled"] is True
    
    @pytest.mark.asyncio
    async def test_configure_alerts_boolean_values(self, wems_server):
        """Test configuring alerts with boolean values."""
        new_config = {
            "enabled": False,
            "send_email": True,
            "debug_mode": False
        }
        
        result = await wems_server._configure_alerts("tsunami", new_config)
        
        assert_textcontent_result(result)
        assert "Updated tsunami alert configuration" in result[0].text
        
        # Verify boolean values are preserved
        config = wems_server.config["alerts"]["tsunami"]
        assert config["enabled"] is False
        assert config["send_email"] is True
        assert config["debug_mode"] is False
    
    @pytest.mark.asyncio
    async def test_configure_alerts_numeric_values(self, wems_server):
        """Test configuring alerts with various numeric values."""
        new_config = {
            "min_magnitude": 4.5,
            "max_depth": 100.0,
            "timeout_seconds": 30,
            "retry_count": 3,
            "threshold_ratio": 0.75
        }
        
        result = await wems_server._configure_alerts("earthquake", new_config)
        
        assert_textcontent_result(result)
        
        # Verify numeric values and types are preserved
        config = wems_server.config["alerts"]["earthquake"]
        assert config["min_magnitude"] == 4.5
        assert isinstance(config["min_magnitude"], float)
        assert config["max_depth"] == 100.0
        assert isinstance(config["max_depth"], float)
        assert config["timeout_seconds"] == 30
        assert isinstance(config["timeout_seconds"], int)
        assert config["retry_count"] == 3
        assert isinstance(config["retry_count"], int)
        assert config["threshold_ratio"] == 0.75
        assert isinstance(config["threshold_ratio"], float)
    
    @pytest.mark.asyncio
    async def test_configure_alerts_string_values(self, wems_server):
        """Test configuring alerts with string values."""
        new_config = {
            "webhook": "https://new-endpoint.example.com/alerts",
            "format": "json",
            "timezone": "UTC",
            "log_level": "INFO"
        }
        
        result = await wems_server._configure_alerts("solar", new_config)
        
        assert_textcontent_result(result)
        
        # Verify string values are preserved
        config = wems_server.config["alerts"]["solar"]
        assert config["webhook"] == "https://new-endpoint.example.com/alerts"
        assert config["format"] == "json"
        assert config["timezone"] == "UTC" 
        assert config["log_level"] == "INFO"
    
    @pytest.mark.asyncio
    async def test_configure_alerts_list_values(self, wems_server):
        """Test configuring alerts with list values."""
        new_config = {
            "alert_levels": ["NORMAL", "ADVISORY", "WATCH", "WARNING"],
            "regions": ["Alaska", "Hawaii", "California"],
            "event_types": ["eruption", "ash", "lava"],
            "notification_methods": []  # Empty list
        }
        
        result = await wems_server._configure_alerts("volcano", new_config)
        
        assert_textcontent_result(result)
        
        # Verify list values are preserved
        config = wems_server.config["alerts"]["volcano"]
        assert config["alert_levels"] == ["NORMAL", "ADVISORY", "WATCH", "WARNING"]
        assert config["regions"] == ["Alaska", "Hawaii", "California"]
        assert config["event_types"] == ["eruption", "ash", "lava"]
        assert config["notification_methods"] == []
    
    @pytest.mark.asyncio
    async def test_configure_alerts_mixed_types(self, wems_server):
        """Test configuring alerts with mixed data types."""
        new_config = {
            "enabled": True,  # boolean
            "min_magnitude": 5.5,  # float
            "max_events": 10,  # int
            "webhook": "https://example.com",  # string
            "regions": ["pacific", "atlantic"],  # list
            "advanced": {  # dict
                "retry": True,
                "timeout": 30.5
            },
            "disabled_features": None  # None
        }
        
        result = await wems_server._configure_alerts("tsunami", new_config)
        
        assert_textcontent_result(result)
        
        # Verify all data types are preserved correctly
        config = wems_server.config["alerts"]["tsunami"]
        assert config["enabled"] is True
        assert config["min_magnitude"] == 5.5
        assert config["max_events"] == 10
        assert config["webhook"] == "https://example.com"
        assert config["regions"] == ["pacific", "atlantic"]
        assert config["advanced"]["retry"] is True
        assert config["advanced"]["timeout"] == 30.5
        assert config["disabled_features"] is None