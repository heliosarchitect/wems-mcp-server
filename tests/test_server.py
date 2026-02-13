"""
Tests for the core WemsServer class functionality.
"""

import asyncio
import os
import tempfile
import pytest
import yaml
from unittest.mock import patch, AsyncMock

from wems_mcp_server import WemsServer


class TestWemsServerInit:
    """Test WemsServer initialization."""
    
    def test_init_with_config_file(self, temp_config_file):
        """Test server initialization with config file."""
        server = WemsServer(temp_config_file)
        
        assert server.config is not None
        assert "alerts" in server.config
        assert server.config["alerts"]["earthquake"]["min_magnitude"] == 5.0
        assert server.http_client is not None
    
    def test_init_without_config_file(self):
        """Test server initialization without config file (uses defaults)."""
        server = WemsServer()
        
        assert server.config is not None
        assert "alerts" in server.config
        # Check default values
        assert server.config["alerts"]["earthquake"]["min_magnitude"] == 6.0
        assert server.config["alerts"]["solar"]["min_kp_index"] == 7
        assert server.http_client is not None
    
    def test_init_with_nonexistent_config_file(self):
        """Test server initialization with non-existent config file (uses defaults)."""
        server = WemsServer("/nonexistent/config.yaml")
        
        assert server.config is not None
        assert "alerts" in server.config
        # Should use defaults when file doesn't exist
        assert server.config["alerts"]["earthquake"]["min_magnitude"] == 6.0
    
    def test_init_with_env_config_path(self, temp_config_file):
        """Test server initialization using WEMS_CONFIG environment variable."""
        with patch.dict(os.environ, {'WEMS_CONFIG': temp_config_file}):
            server = WemsServer()  # No explicit config path
            
            assert server.config is not None
            assert server.config["alerts"]["earthquake"]["min_magnitude"] == 5.0
    
    def test_config_loading_invalid_yaml(self):
        """Test config loading with invalid YAML file."""
        # Create invalid YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [unclosed")
            invalid_config_path = f.name
        
        try:
            # The actual implementation raises YAML errors, it doesn't fall back to defaults
            with pytest.raises(yaml.YAMLError):
                server = WemsServer(invalid_config_path)
        finally:
            os.unlink(invalid_config_path)


class TestWemsServerAsyncContext:
    """Test WemsServer async context manager functionality."""
    
    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test server as async context manager."""
        async with WemsServer() as server:
            assert server is not None
            assert server.http_client is not None
            assert not server.http_client.is_closed
        
        # After exiting context, http_client should be closed
        assert server.http_client.is_closed
    
    @pytest.mark.asyncio
    async def test_async_enter(self):
        """Test __aenter__ method."""
        server = WemsServer()
        result = await server.__aenter__()
        assert result is server
        await server.http_client.aclose()
    
    @pytest.mark.asyncio
    async def test_async_exit(self):
        """Test __aexit__ method."""
        server = WemsServer()
        assert not server.http_client.is_closed
        
        await server.__aexit__(None, None, None)
        assert server.http_client.is_closed


class TestWemsServerConfiguration:
    """Test configuration management functionality."""
    
    def test_load_config_with_complex_structure(self):
        """Test loading config with complex nested structure."""
        complex_config = {
            "alerts": {
                "earthquake": {
                    "min_magnitude": 5.5,
                    "webhook": "https://example.com/webhook",
                    "regions": ["california", "japan"]
                },
                "solar": {
                    "min_kp_index": 6.5,
                    "webhook": "https://example.com/solar",
                    "event_types": ["flare", "cme"]
                },
                "volcano": {
                    "alert_levels": ["WARNING"],
                    "webhook": None,
                    "enabled": False
                },
                "tsunami": {
                    "enabled": True,
                    "webhook": "https://example.com/tsunami",
                    "regions": ["pacific"]
                }
            },
            "general": {
                "timeout": 45,
                "retry_count": 3
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(complex_config, f)
            config_path = f.name
        
        try:
            server = WemsServer(config_path)
            
            assert server.config["alerts"]["earthquake"]["min_magnitude"] == 5.5
            assert server.config["alerts"]["earthquake"]["regions"] == ["california", "japan"]
            assert server.config["alerts"]["solar"]["min_kp_index"] == 6.5
            assert server.config["alerts"]["volcano"]["enabled"] is False
            assert server.config["general"]["timeout"] == 45
            
        finally:
            os.unlink(config_path)
    
    def test_load_config_with_empty_file(self):
        """Test loading config from empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("")  # Empty file
            empty_config_path = f.name
        
        try:
            server = WemsServer(empty_config_path)
            # Empty YAML file returns None, so config will be None in this implementation
            assert server.config is None
            
        finally:
            os.unlink(empty_config_path)


class TestWemsServerTools:
    """Test tool registration functionality."""
    
    def test_server_has_tool_methods(self, wems_server_default):
        """Test that server has all expected tool methods."""
        expected_tool_methods = [
            "_check_earthquakes",
            "_check_solar", 
            "_check_volcanoes",
            "_check_tsunamis",
            "_configure_alerts"
        ]
        
        for method_name in expected_tool_methods:
            assert hasattr(wems_server_default, method_name)
            assert callable(getattr(wems_server_default, method_name))
    
    def test_server_has_mcp_handlers_registered(self, wems_server_default):
        """Test that MCP handlers are properly registered."""
        from mcp.types import ListToolsRequest, CallToolRequest
        
        handlers = wems_server_default.server.request_handlers
        assert ListToolsRequest in handlers
        assert CallToolRequest in handlers


class TestWemsServerHTTPClientManagement:
    """Test HTTP client lifecycle management."""
    
    def test_http_client_created_on_init(self):
        """Test that HTTP client is created during initialization."""
        server = WemsServer()
        assert server.http_client is not None
        assert hasattr(server.http_client, 'get')
        assert hasattr(server.http_client, 'post')
        assert server.http_client.timeout.read == 30.0
    
    @pytest.mark.asyncio
    async def test_http_client_closes_properly(self):
        """Test that HTTP client closes properly."""
        server = WemsServer()
        assert not server.http_client.is_closed
        
        await server.http_client.aclose()
        assert server.http_client.is_closed
    
    @pytest.mark.asyncio
    async def test_multiple_close_calls_safe(self):
        """Test that multiple close calls on HTTP client are safe."""
        server = WemsServer()
        
        # First close
        await server.http_client.aclose()
        assert server.http_client.is_closed
        
        # Second close should not raise an error
        await server.http_client.aclose()
        assert server.http_client.is_closed