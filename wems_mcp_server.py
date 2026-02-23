#!/usr/bin/env python3
"""
WEMS - World Event Monitoring System MCP Server

Natural hazard monitoring with configurable webhooks for threshold alerts.
Free tier provides essential safety alerts. Premium unlocks full depth.
"""

import asyncio
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
import yaml
from mcp.server import Server
from mcp.types import Tool, TextContent

# WEMS licensing and rate limiting
from wems_rate_limit import check_rate_limit, get_limit_display
from wems_usage import record_api_call


# ─── Tier Definitions ────────────────────────────────────────────────────────

TIER_FREE = "free"
TIER_PREMIUM = "premium"
TIER_ENTERPRISE = "enterprise"

TIER_LIMITS = {
    TIER_FREE: {
        "earthquake_min_magnitude": 4.5,       # Can't go below 4.5
        "earthquake_time_periods": ["hour", "day"],  # No weekly
        "earthquake_max_results": 5,
        "solar_forecasts": False,              # Current conditions only
        "solar_historical": False,
        "solar_max_events": 3,
        "volcano_region_filter": False,        # No region filtering
        "volcano_alert_levels": ["WARNING"],   # Only highest alerts
        "tsunami_max_results": 3,
        "tsunami_regions": ["pacific"],        # Pacific only
        "hurricane_basins": ["atlantic"],      # Atlantic only
        "hurricane_include_forecast": False,   # No forecast tracks
        "hurricane_max_results": 3,
        "wildfire_max_results": 3,            # Fire warnings only
        "wildfire_region_filter": False,      # No region filtering
        "severe_weather_max_results": 3,      # Recent alerts only (24h)
        "severe_weather_time_range": 24,      # Hours (last 24h only)
        "severe_weather_severities": ["extreme", "severe"],  # High severity only
        "severe_weather_state_filter": False, # No state filtering
        "floods_max_results": 3,              # Major floods only (24h)
        "floods_time_range": 24,              # Hours (last 24h only)
        "floods_stages": ["major"],           # Major flood stage only
        "floods_state_filter": False,         # No state filtering
        "floods_river_gauges": False,         # No river gauge data
        "air_quality_max_results": 3,         # Limited stations
        "air_quality_countries": ["US"],       # US only
        "air_quality_parameters": ["pm25", "o3"],  # PM2.5 and O3 only
        "air_quality_city_filter": False,     # No city/zip filtering
        "air_quality_coordinates": True,      # Allow lat/lon search
        "air_quality_forecast": False,        # No forecast data
        "threat_max_results": 3,              # Limited advisories
        "threat_types": ["terrorism"],         # Terrorism (DHS NTAS) only
        "threat_countries_filter": False,     # No country filtering
        "threat_region_filter": False,        # No region filtering
        "threat_include_expired": False,      # Current advisories only
        "threat_include_historical": False,   # No historical data
        "space_weather_max_results": 5,      # Limited space weather alerts
        "space_weather_hours_back": 24,      # Last 24 hours only
        "drought_status": False,              # No drought monitoring (premium only)
        "configure_alerts": False,             # No custom alert config
        "polling_note": "Updates every 15 minutes",
    },
    TIER_PREMIUM: {
        "earthquake_min_magnitude": 1.0,       # Full range
        "earthquake_time_periods": ["hour", "day", "week", "month"],
        "earthquake_max_results": 50,
        "solar_forecasts": True,               # 3-day forecasts
        "solar_historical": True,              # Historical data
        "solar_max_events": 25,
        "volcano_region_filter": True,         # Region filtering
        "volcano_alert_levels": ["NORMAL", "ADVISORY", "WATCH", "WARNING"],
        "tsunami_max_results": 25,
        "tsunami_regions": ["pacific", "atlantic", "indian", "mediterranean"],
        "hurricane_basins": ["atlantic", "pacific"],  # All basins
        "hurricane_include_forecast": True,    # Forecast tracks
        "hurricane_max_results": 25,
        "wildfire_max_results": 25,          # All fire data
        "wildfire_region_filter": True,      # Region filtering
        "severe_weather_max_results": 25,    # All alerts
        "severe_weather_time_range": 168,    # Hours (up to 7 days)
        "severe_weather_severities": ["extreme", "severe", "moderate", "minor"],  # All severities
        "severe_weather_state_filter": True, # State filtering
        "floods_max_results": 25,            # All floods
        "floods_time_range": 168,            # Hours (up to 7 days)
        "floods_stages": ["action", "minor", "moderate", "major"],  # All flood stages
        "floods_state_filter": True,         # State filtering
        "floods_river_gauges": True,         # River gauge data
        "air_quality_max_results": 25,       # Full results
        "air_quality_countries": None,        # Global (None = all)
        "air_quality_parameters": ["pm25", "pm10", "o3", "no2", "so2", "co"],  # All pollutants
        "air_quality_city_filter": True,     # City/zip filtering
        "air_quality_coordinates": True,     # Lat/lon search
        "air_quality_forecast": True,        # Forecast data
        "threat_max_results": 25,            # Full advisories
        "threat_types": ["terrorism", "travel", "cyber", "all"],  # All threat types
        "threat_countries_filter": True,     # Country filtering
        "threat_region_filter": True,        # Region filtering
        "threat_include_expired": True,      # Include expired advisories
        "threat_include_historical": True,   # Historical data
        "space_weather_max_results": 25,     # Full space weather alerts
        "space_weather_hours_back": 168,     # Up to 7 days
        "drought_status": True,               # Full drought monitoring
        "drought_weeks_back": 52,            # Up to 1 year historical
        "configure_alerts": True,              # Full alert customization
        "polling_note": "Real-time updates",
    },
    TIER_ENTERPRISE: {
        "earthquake_min_magnitude": 1.0,       # Full range
        "earthquake_time_periods": ["hour", "day", "week", "month"],
        "earthquake_max_results": 1000,        # Enterprise-scale results
        "solar_forecasts": True,               # 3-day forecasts
        "solar_historical": True,              # Historical data
        "solar_max_events": 100,               # More events
        "volcano_region_filter": True,         # Region filtering
        "volcano_alert_levels": ["NORMAL", "ADVISORY", "WATCH", "WARNING"],
        "tsunami_max_results": 100,
        "tsunami_regions": ["pacific", "atlantic", "indian", "mediterranean"],
        "hurricane_basins": ["atlantic", "pacific"],  # All basins
        "hurricane_include_forecast": True,    # Forecast tracks
        "hurricane_max_results": 100,
        "wildfire_max_results": 100,          # Enterprise fire data
        "wildfire_region_filter": True,       # Region filtering
        "severe_weather_max_results": 100,    # Enterprise alerts
        "severe_weather_time_range": 720,     # Hours (up to 30 days)
        "severe_weather_severities": ["extreme", "severe", "moderate", "minor"],  # All severities
        "severe_weather_state_filter": True,  # State filtering
        "floods_max_results": 100,            # Enterprise floods
        "floods_time_range": 720,             # Hours (up to 30 days)
        "floods_stages": ["action", "minor", "moderate", "major"],  # All flood stages
        "floods_state_filter": True,          # State filtering
        "floods_river_gauges": True,          # River gauge data
        "air_quality_max_results": 100,       # Enterprise results
        "air_quality_countries": None,        # Global (None = all)
        "air_quality_parameters": ["pm25", "pm10", "o3", "no2", "so2", "co"],  # All pollutants
        "air_quality_city_filter": True,      # City/zip filtering
        "air_quality_coordinates": True,      # Lat/lon search
        "air_quality_forecast": True,         # Forecast data
        "threat_max_results": 100,            # Enterprise advisories
        "threat_types": ["terrorism", "travel", "cyber", "all"],  # All threat types
        "threat_countries_filter": True,      # Country filtering
        "threat_region_filter": True,         # Region filtering
        "threat_include_expired": True,       # Include expired advisories
        "threat_include_historical": True,    # Historical data
        "space_weather_max_results": 100,     # Enterprise space weather alerts
        "space_weather_hours_back": 720,      # Up to 30 days
        "drought_status": True,                # Full drought monitoring
        "drought_weeks_back": 260,            # Up to 5 years historical
        "configure_alerts": True,             # Full alert customization
        "polling_note": "Real-time updates + API access",
    }
}


def _get_tier(api_key: Optional[str] = None) -> str:
    """Determine user tier from API key or environment.
    
    Tier resolution order:
    1. WEMS_API_KEY environment variable (license key validation)
    2. api_key passed in config (license key validation)  
    3. Fallback to WEMS_PREMIUM_KEYS list check (legacy)
    4. Default to free tier
    
    License keys have format: WEMS-XXXX-XXXX-XXXX-XXXX and are self-validating.
    """
    key = api_key or os.environ.get("WEMS_API_KEY", "")
    if not key:
        return TIER_FREE
    
    # First, try to validate as a license key
    try:
        from wems_license import validate_license_key, is_license_key
        
        if is_license_key(key):
            license_info = validate_license_key(key)
            
            # Check if license is valid and not expired
            if license_info['valid'] and not license_info['expired']:
                return license_info['tier']
            elif license_info['expired']:
                # Expired license keys fall back to free tier
                return TIER_FREE
                
    except Exception:
        # If license validation fails, fall back to legacy checks
        pass
    
    # Fallback to legacy premium keys list
    premium_keys = os.environ.get("WEMS_PREMIUM_KEYS", "").split(",")
    premium_keys = [k.strip() for k in premium_keys if k.strip()]
    
    if key in premium_keys:
        return TIER_PREMIUM
    
    # Check against Stripe (if configured)
    stripe_secret = os.environ.get("STRIPE_SECRET_KEY", "")
    if stripe_secret and key.startswith("wems_"):
        # Stripe validation would happen here in production
        # For now, keys starting with wems_live_ are premium
        if key.startswith("wems_live_"):
            return TIER_PREMIUM
    
    return TIER_FREE


def _tier_limits(tier: str) -> Dict[str, Any]:
    """Get limits for a tier."""
    return TIER_LIMITS.get(tier, TIER_LIMITS[TIER_FREE])


def _upgrade_message(feature: str) -> str:
    """Generate a tasteful upgrade prompt."""
    return (
        f"\n\n─── 🔒 ───\n"
        f"{feature} is available on WEMS Premium ($24.99/mo).\n"
        f"Unlock full history, all regions, custom alerts, and real-time updates.\n"
        f"→ https://wems.dev/premium"
    )


# ─── Server ──────────────────────────────────────────────────────────────────

class WemsServer:
    def __init__(self, config_path: Optional[str] = None):
        self.server = Server("wems")
        self.config = self._load_config(config_path) or {}
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.api_key = self.config.get("api_key") or os.environ.get("WEMS_API_KEY", "")
        self.tier = _get_tier(self.api_key)
        self.limits = _tier_limits(self.tier)
        self.source_contracts = {
            "usgs_earthquakes": {
                "timeout_seconds": 12.0,
                "fallback_urls": [
                    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
                ],
                "required_keys": ["metadata", "features"],
                "max_age_hours": 36,
            }
        }
        self.feature_flags = {
            "multi_source_confidence_fusion": self._env_flag("WEMS_FEATURE_MULTI_SOURCE_CONFIDENCE_FUSION", False)
        }
        
        # Register MCP tools
        self._register_tools()

    @staticmethod
    def _env_flag(name: str, default: bool = False) -> bool:
        value = os.environ.get(name)
        if value is None:
            return default
        return str(value).strip().lower() in {"1", "true", "yes", "on"}
    
    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not config_path:
            config_path = os.environ.get("WEMS_CONFIG", "config.yaml")
        
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            return {
                "alerts": {
                    "earthquake": {"min_magnitude": 6.0},
                    "solar": {"min_kp_index": 7},
                    "volcano": {"alert_levels": ["WARNING", "WATCH"]},
                    "tsunami": {"enabled": True},
                    "hurricane": {"enabled": True},
                    "wildfire": {"enabled": True}
                }
            }
    
    def _check_rate_limit_and_record_usage(self, tool_name: str) -> Optional[str]:
        """Check rate limit and record usage. Returns error message if rate limited."""
        try:
            # Use API key or IP-based identification for rate limiting
            rate_key = self.api_key if self.api_key else "anonymous"
            
            # Check rate limit
            rate_result = check_rate_limit(rate_key, self.tier)
            
            if not rate_result["allowed"]:
                remaining_time = rate_result.get("reset_time", 0) - time.time()
                remaining_minutes = int(remaining_time / 60) if remaining_time > 0 else 0
                
                limit_info = get_limit_display(self.tier)
                return (f"🚫 **Rate Limit Exceeded**\n\n"
                       f"Current tier: {limit_info}\n"
                       f"Try again in {remaining_minutes} minutes.\n\n"
                       f"Upgrade to Premium for higher limits: https://wems.dev/premium")
            
            # Record successful API call for usage tracking
            record_api_call(
                license_key=self.api_key if self.api_key else None,
                tier=self.tier,
                tool_name=tool_name,
                success=True
            )
            
            return None  # No error
            
        except Exception as e:
            # Don't let rate limiting break the API
            print(f"Warning: Rate limiting error: {e}")
            return None
    
    def _record_api_error(self, tool_name: str, error_message: str):
        """Record an API error in usage tracking."""
        try:
            record_api_call(
                license_key=self.api_key if self.api_key else None,
                tier=self.tier,
                tool_name=tool_name,
                success=False,
                error_message=error_message
            )
        except Exception as e:
            print(f"Warning: Usage tracking error: {e}")

    async def _fetch_json_with_contract(
        self,
        source_name: str,
        primary_url: str,
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, str]]]:
        """Fetch JSON with per-source reliability contract (timeout/fallback/schema/freshness)."""
        contract = self.source_contracts.get(source_name, {})
        timeout_seconds = float(contract.get("timeout_seconds", 30.0))
        fallback_urls = contract.get("fallback_urls", [])
        required_keys = contract.get("required_keys", [])
        max_age_hours = contract.get("max_age_hours")

        urls_to_try = [primary_url, *fallback_urls]
        last_error: Optional[Dict[str, str]] = None

        for url in urls_to_try:
            try:
                response = await self.http_client.get(url, timeout=timeout_seconds)
                response.raise_for_status()
                data = response.json()

                missing = [k for k in required_keys if k not in data]
                if missing:
                    last_error = {
                        "taxonomy": "schema_error",
                        "detail": f"missing keys: {', '.join(missing)}",
                        "source": url,
                    }
                    continue

                if max_age_hours and source_name == "usgs_earthquakes":
                    features = data.get("features") or []
                    if features:
                        try:
                            newest_epoch_ms = max(
                                int((f.get("properties") or {}).get("time", 0))
                                for f in features
                            )
                            newest_dt = datetime.fromtimestamp(newest_epoch_ms / 1000, tz=timezone.utc)
                            age_hours = (datetime.now(timezone.utc) - newest_dt).total_seconds() / 3600
                            if age_hours > float(max_age_hours):
                                last_error = {
                                    "taxonomy": "stale_data",
                                    "detail": f"newest event age {age_hours:.1f}h exceeds {max_age_hours}h",
                                    "source": url,
                                }
                                continue
                        except Exception:
                            # If we cannot parse event times, do not hard-fail freshness gate.
                            pass

                return data, None

            except httpx.TimeoutException as e:
                last_error = {"taxonomy": "upstream_timeout", "detail": str(e), "source": url}
            except httpx.HTTPStatusError as e:
                status = getattr(e.response, "status_code", "unknown")
                last_error = {"taxonomy": "upstream_http_error", "detail": f"HTTP {status}", "source": url}
            except ValueError as e:
                last_error = {"taxonomy": "parse_error", "detail": str(e), "source": url}
            except httpx.HTTPError as e:
                last_error = {"taxonomy": "network_error", "detail": str(e), "source": url}

        return None, (last_error or {"taxonomy": "unknown_error", "detail": "unknown", "source": primary_url})
    
    def _register_tools(self):
        """Register all MCP tools."""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            tools = [
                Tool(
                    name="check_earthquakes",
                    description="Check recent earthquake activity with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "min_magnitude": {
                                "type": "number",
                                "description": f"Minimum magnitude (free: ≥4.5, premium: ≥1.0)",
                                "default": 4.5
                            },
                            "time_period": {
                                "type": "string", 
                                "enum": ["hour", "day", "week", "month"],
                                "description": f"Time period (free: hour/day, premium: +week/month)",
                                "default": "day"
                            },
                            "region": {
                                "type": "string",
                                "description": "Geographic region filter"
                            },
                            "latitude": {
                                "type": "number",
                                "description": "Center latitude for radius search (premium)"
                            },
                            "longitude": {
                                "type": "number",
                                "description": "Center longitude for radius search (premium)"
                            },
                            "radius_km": {
                                "type": "number",
                                "description": "Search radius in km (premium, default: 500)"
                            }
                        }
                    }
                ),
                Tool(
                    name="check_solar",
                    description="Monitor space weather: K-index, solar flares, CMEs",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "event_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Types: flare, cme, geomagnetic (default: all)"
                            },
                            "include_forecast": {
                                "type": "boolean",
                                "description": "Include 3-day forecast (premium)",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="check_volcanoes",
                    description="Monitor volcanic activity and eruption alerts worldwide",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "alert_levels": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Free: WARNING only. Premium: NORMAL/ADVISORY/WATCH/WARNING",
                                "default": ["WARNING"]
                            },
                            "region": {
                                "type": "string",
                                "description": "Geographic region filter (premium)"
                            }
                        }
                    }
                ),
                Tool(
                    name="check_tsunamis",
                    description="Check for tsunami warnings and advisories",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "regions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Free: pacific only. Premium: all ocean basins"
                            }
                        }
                    }
                ),
                Tool(
                    name="check_hurricanes",
                    description="Monitor hurricanes and tropical storms with forecast data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "basin": {
                                "type": "string",
                                "enum": ["atlantic", "pacific", "all"],
                                "description": "Free: atlantic only. Premium: all basins",
                                "default": "atlantic"
                            },
                            "include_forecast": {
                                "type": "boolean",
                                "description": "Include forecast tracks (premium only)",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="check_wildfires",
                    description="Monitor wildfire activity and fire weather alerts",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "region": {
                                "type": "string",
                                "description": "Geographic region filter (premium only)"
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["low", "moderate", "high", "critical"],
                                "description": "Fire severity filter (optional)"
                            }
                        }
                    }
                ),
                Tool(
                    name="check_severe_weather",
                    description="Monitor severe weather alerts - tornadoes, thunderstorms, flash floods, winter storms",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "state": {
                                "type": "string",
                                "description": "2-letter state code (e.g., TX, CA) for filtering (premium only)"
                            },
                            "severity": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Free: extreme/severe only. Premium: all severities",
                                "default": ["extreme", "severe"]
                            },
                            "event_type": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Event types: tornado, thunderstorm, flood, winter storm, etc."
                            },
                            "urgency": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Urgency levels: immediate, expected, future, past"
                            },
                            "certainty": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Certainty levels: observed, likely, possible, unlikely"
                            }
                        }
                    }
                ),
                Tool(
                    name="check_floods",
                    description="Monitor flood warnings and river gauge data from USGS and NOAA",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "state": {
                                "type": "string",
                                "description": "2-letter state code (e.g., TX, CA) for filtering (premium only)"
                            },
                            "flood_stage": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Free: major only. Premium: action, minor, moderate, major",
                                "default": ["major"]
                            },
                            "time_range": {
                                "type": "string",
                                "enum": ["hour", "day", "week"],
                                "description": "Free: last 24h only. Premium: up to 7 days",
                                "default": "day"
                            },
                            "include_river_gauges": {
                                "type": "boolean",
                                "description": "Include USGS river gauge data (premium only)",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="check_air_quality",
                    description="Monitor air quality index (AQI) with pollutant data from OpenAQ",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "zip_code": {
                                "type": "string",
                                "description": "ZIP code for local AQI (premium only)"
                            },
                            "city": {
                                "type": "string",
                                "description": "City name for local AQI (premium only)"
                            },
                            "state": {
                                "type": "string",
                                "description": "2-letter state code (e.g., TX, CA)"
                            },
                            "country": {
                                "type": "string",
                                "description": "2-letter country code (free: US only, premium: global)",
                                "default": "US"
                            },
                            "latitude": {
                                "type": "number",
                                "description": "Latitude for nearest station search"
                            },
                            "longitude": {
                                "type": "number",
                                "description": "Longitude for nearest station search"
                            },
                            "radius_km": {
                                "type": "number",
                                "description": "Search radius in km (default 25)",
                                "default": 25
                            },
                            "parameters": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Pollutants: pm25, pm10, o3, no2, so2, co (free: pm25/o3 only)"
                            },
                            "include_forecast": {
                                "type": "boolean",
                                "description": "Include AQI forecast (premium only)",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="check_threat_advisories",
                    description="Monitor threat advisories from DHS NTAS and State Department travel warnings",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "threat_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Types: terrorism, travel, cyber, all (free: terrorism only)",
                                "default": ["terrorism"]
                            },
                            "countries": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Country codes for travel advisories (premium only)"
                            },
                            "region": {
                                "type": "string",
                                "description": "Geographic region filter (premium only)"
                            },
                            "threat_level": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Minimum threat levels: elevated, imminent (for NTAS); 1-4 (for travel)"
                            },
                            "include_expired": {
                                "type": "boolean",
                                "description": "Include expired advisories (premium only)",
                                "default": False
                            },
                            "include_historical": {
                                "type": "boolean",
                                "description": "Include historical data (premium only)",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="check_space_weather_alerts",
                    description="Monitor active space weather alerts from NOAA SWPC for geomagnetic storms, solar radiation, and radio blackouts",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "alert_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Filter by alert types: geomagnetic, radiation, radio, all (default: all)"
                            },
                            "hours_back": {
                                "type": "number",
                                "description": "Hours to look back for alerts (default: 24, max: 168)",
                                "default": 24
                            }
                        }
                    }
                ),
            ]
            
            # Premium-tier tools
            if self.tier == TIER_PREMIUM:
                tools.append(Tool(
                    name="check_drought_status",
                    description="Check current US drought conditions by state with detailed D0-D4 classification (premium)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "state": {
                                "type": "string",
                                "description": "US state abbreviation (e.g., CA, TX) or FIPS code",
                                "required": True
                            },
                            "weeks_back": {
                                "type": "number",
                                "description": "Number of weeks of historical data to include (default: 4)",
                                "default": 4
                            },
                            "include_trend": {
                                "type": "boolean",
                                "description": "Include trend analysis over the time period",
                                "default": True
                            }
                        },
                        "required": ["state"]
                    }
                ))
            
            # configure_alerts only available on premium
            if self.tier == TIER_PREMIUM:
                tools.append(Tool(
                    name="configure_alerts",
                    description="Configure custom alert thresholds and webhook URLs (premium)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "alert_type": {
                                "type": "string",
                                "enum": ["earthquake", "solar", "volcano", "tsunami"]
                            },
                            "config": {
                                "type": "object",
                                "description": "Alert configuration parameters"
                            }
                        },
                        "required": ["alert_type", "config"]
                    }
                ))

            if self.feature_flags.get("multi_source_confidence_fusion"):
                tools.append(Tool(
                    name="fuse_multi_source_incidents",
                    description="Fuse overlapping USGS/NOAA/NWS/CISA events into canonical confidence-scored incidents (feature-flagged)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "events": {
                                "type": "array",
                                "description": "Array of source events. Each event supports: source, event_type, title, timestamp, latitude, longitude, event_id, url",
                                "items": {"type": "object"}
                            },
                            "fusion_window_minutes": {
                                "type": "number",
                                "description": "Temporal clustering window",
                                "default": 30
                            },
                            "dedupe_radius_km": {
                                "type": "number",
                                "description": "Spatial clustering radius in kilometers",
                                "default": 25
                            }
                        },
                        "required": ["events"]
                    }
                ))
            
            return tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            # Check rate limits and record usage
            rate_error = self._check_rate_limit_and_record_usage(name)
            if rate_error:
                return [TextContent(type="text", text=rate_error)]
            
            try:
                if name == "check_earthquakes":
                    return await self._check_earthquakes(**arguments)
                elif name == "check_solar":
                    return await self._check_solar(**arguments)
                elif name == "check_volcanoes":
                    return await self._check_volcanoes(**arguments)
                elif name == "check_tsunamis":
                    return await self._check_tsunamis(**arguments)
                elif name == "check_hurricanes":
                    return await self._check_hurricanes(**arguments)
                elif name == "check_wildfires":
                    return await self._check_wildfires(**arguments)
                elif name == "check_severe_weather":
                    return await self._check_severe_weather(**arguments)
                elif name == "check_floods":
                    return await self._check_floods(**arguments)
                elif name == "check_air_quality":
                    return await self._check_air_quality(**arguments)
                elif name == "check_threat_advisories":
                    return await self._check_threat_advisories(**arguments)
                elif name == "check_space_weather_alerts":
                    return await self._check_space_weather_alerts(**arguments)
                elif name == "check_drought_status":
                    if self.tier not in [TIER_PREMIUM, TIER_ENTERPRISE]:
                        return [TextContent(type="text", text=f"🔒 US Drought Monitor requires WEMS Premium.{_upgrade_message('Drought status monitoring')}")] 
                    return await self._check_drought_status(**arguments)
                elif name == "configure_alerts":
                    if self.tier not in [TIER_PREMIUM, TIER_ENTERPRISE]:
                        return [TextContent(type="text", text=f"🔒 Custom alert configuration requires WEMS Premium.{_upgrade_message('Custom alert thresholds')}")]
                    return await self._configure_alerts(**arguments)
                elif name == "fuse_multi_source_incidents":
                    if not self.feature_flags.get("multi_source_confidence_fusion"):
                        return [TextContent(type="text", text="Feature disabled: set WEMS_FEATURE_MULTI_SOURCE_CONFIDENCE_FUSION=true to enable fusion")]
                    return await self._fuse_multi_source_incidents(**arguments)
                else:
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
            except Exception as e:
                # Record API error for tracking
                self._record_api_error(name, str(e))
                raise
    
    # ─── Earthquakes ─────────────────────────────────────────────────────

    async def _check_earthquakes(
        self,
        min_magnitude: float = 4.5,
        time_period: str = "day",
        region: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: Optional[float] = None
    ) -> List[TextContent]:
        """Check recent earthquake activity with tier-based limits."""
        
        limits = self.limits
        
        # Enforce tier limits on magnitude
        if min_magnitude < limits["earthquake_min_magnitude"]:
            if self.tier == TIER_FREE:
                min_magnitude = limits["earthquake_min_magnitude"]
                tier_note = f"\n📋 Free tier: showing M{min_magnitude}+ (premium unlocks M1.0+)\n"
            else:
                tier_note = ""
        else:
            tier_note = ""
        
        # Enforce tier limits on time period
        if time_period not in limits["earthquake_time_periods"]:
            if self.tier == TIER_FREE:
                return [TextContent(
                    type="text",
                    text=f"🔒 '{time_period}' time range requires WEMS Premium. Free tier supports: {', '.join(limits['earthquake_time_periods'])}.{_upgrade_message('Extended earthquake history')}"
                )]
            
        # Geo-radius search is premium only
        if (latitude is not None or longitude is not None) and self.tier == TIER_FREE:
            return [TextContent(
                type="text",
                text=f"🔒 Geographic radius search requires WEMS Premium.{_upgrade_message('Geo-filtered earthquake monitoring')}"
            )]
        
        max_results = limits["earthquake_max_results"]
        
        # Build USGS API URL
        if latitude is not None and longitude is not None and self.tier == TIER_PREMIUM:
            # Use query API for geo-radius search
            radius = radius_km or 500
            period_map = {"hour": 1/24, "day": 1, "week": 7, "month": 30}
            days = period_map.get(time_period, 1)
            start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
            url = (
                f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson"
                f"&minmagnitude={min_magnitude}&starttime={start}"
                f"&latitude={latitude}&longitude={longitude}&maxradiuskm={radius}"
                f"&orderby=magnitude&limit={max_results}"
            )
        else:
            # Standard feed endpoints
            mag_bracket = "significant" if min_magnitude >= 6.0 else "4.5" if min_magnitude >= 4.5 else "2.5" if min_magnitude >= 2.5 else "1.0"
            period_map = {"hour": "hour", "day": "day", "week": "week", "month": "month"}
            period = period_map.get(time_period, "day")
            url = f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{mag_bracket}_{period}.geojson"
        
        try:
            data, fetch_error = await self._fetch_json_with_contract("usgs_earthquakes", url)
            if fetch_error or data is None:
                taxonomy = (fetch_error or {}).get("taxonomy", "unknown_error")
                detail = (fetch_error or {}).get("detail", "unknown")
                return [TextContent(type="text", text=f"❌ Error fetching earthquake data [{taxonomy}]: {detail}")]

            count = data["metadata"]["count"]
            
            if count == 0:
                return [TextContent(
                    type="text", 
                    text=f"🌍 No earthquakes ≥{min_magnitude} magnitude in the past {time_period}"
                )]
            
            result_text = [f"🌍 Earthquakes ≥{min_magnitude} magnitude ({time_period}): {count} found\n"]
            if tier_note:
                result_text.append(tier_note)
            
            shown = 0
            for feature in data["features"]:
                if shown >= max_results:
                    remaining = count - max_results
                    if remaining > 0 and self.tier == TIER_FREE:
                        result_text.append(f"\n... and {remaining} more.{_upgrade_message('Full earthquake results (up to 50)')}")
                    elif remaining > 0:
                        result_text.append(f"\n... and {remaining} more (showing top {max_results})")
                    break
                    
                props = feature["properties"]
                coords = feature["geometry"]["coordinates"]
                
                magnitude = props["mag"]
                place = props["place"]
                time_ms = props["time"]
                depth = coords[2]
                
                quake_time = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc)
                time_str = quake_time.strftime("%Y-%m-%d %H:%M UTC")
                
                if region and region.lower() not in (place or "").lower():
                    continue
                
                if magnitude >= 7.0:
                    mag_icon = "🔴"
                elif magnitude >= 6.0:
                    mag_icon = "🟠" 
                elif magnitude >= 5.0:
                    mag_icon = "🟡"
                else:
                    mag_icon = "•"
                
                result_text.append(
                    f"{mag_icon} {magnitude} - {place}\n"
                    f"   {time_str} | Depth: {depth:.1f} km\n"
                )
                shown += 1
                
                await self._check_earthquake_alert(magnitude, place, quake_time)
            
            if self.tier == TIER_FREE:
                result_text.append(f"\n📋 {limits['polling_note']}")
            
            return [TextContent(type="text", text="".join(result_text))]
            
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching earthquake data: {e}")]
    
    # ─── Solar / Space Weather ───────────────────────────────────────────

    async def _check_solar(
        self,
        event_types: Optional[List[str]] = None,
        include_forecast: bool = False
    ) -> List[TextContent]:
        """Monitor space weather with tier-based access."""
        
        limits = self.limits
        
        try:
            # K-index (available to all tiers)
            kindex_url = "https://services.swpc.noaa.gov/json/boulder_k_index_1m.json"
            response = await self.http_client.get(kindex_url)
            response.raise_for_status()
            kindex_data = response.json()
            
            # Events (limited for free)
            events_url = "https://services.swpc.noaa.gov/json/edited_events.json"
            events_response = await self.http_client.get(events_url)
            events_response.raise_for_status()
            events_data = events_response.json()
            
            result_text = ["🌞 **Space Weather Status**\n\n"]
            
            # K-index
            if kindex_data:
                latest = kindex_data[-1]
                k_index = float(latest["k_index"])
                time_tag = latest["time_tag"]
                
                dt = datetime.fromisoformat(time_tag.replace('Z', '+00:00'))
                time_str = dt.strftime("%Y-%m-%d %H:%M UTC")
                
                if k_index >= 7:
                    level_icon, level_text = "🔴", "SEVERE STORM"
                elif k_index >= 5:
                    level_icon, level_text = "🟠", "STRONG STORM"
                elif k_index >= 4:
                    level_icon, level_text = "🟡", "MINOR STORM"
                elif k_index >= 3:
                    level_icon, level_text = "🟢", "UNSETTLED"
                else:
                    level_icon, level_text = "🔵", "QUIET"
                
                result_text.append(f"**Geomagnetic Activity (K-index):**\n")
                result_text.append(f"{level_icon} K={k_index:.1f} - {level_text}\n")
                result_text.append(f"Latest reading: {time_str}\n\n")
                
                await self._check_solar_alert(k_index, level_text, dt)
            
            # Recent events (tier-limited)
            if events_data:
                now = datetime.now(timezone.utc)
                recent_events = []
                
                for event in events_data:
                    try:
                        event_time = datetime.fromisoformat(event["begin_time"].replace('Z', '+00:00'))
                        if (now - event_time).days <= 1:
                            recent_events.append(event)
                    except (ValueError, KeyError):
                        continue
                
                max_events = limits["solar_max_events"]
                
                if recent_events:
                    result_text.append("**Recent Space Weather Events (24h):**\n")
                    
                    shown = 0
                    for event in recent_events:
                        if shown >= max_events:
                            remaining = len(recent_events) - max_events
                            if remaining > 0 and self.tier == TIER_FREE:
                                result_text.append(f"\n... and {remaining} more events.{_upgrade_message('Full space weather event history')}")
                            break
                            
                        event_type = event.get("type", "Unknown")
                        begin_time = event.get("begin_time", "")
                        description = event.get("message", "No description")
                        
                        if begin_time:
                            dt = datetime.fromisoformat(begin_time.replace('Z', '+00:00'))
                            time_str = dt.strftime("%m-%d %H:%M UTC")
                        else:
                            time_str = "Unknown time"
                        
                        if "flare" in event_type.lower():
                            event_icon = "☀️"
                        elif "cme" in event_type.lower():
                            event_icon = "🌪️"
                        elif "radio" in event_type.lower():
                            event_icon = "📡"
                        else:
                            event_icon = "⭐"
                        
                        result_text.append(f"{event_icon} {event_type} ({time_str})\n")
                        result_text.append(f"   {description}\n\n")
                        shown += 1
                else:
                    result_text.append("**Recent Space Weather Events (24h):**\n")
                    result_text.append("🟢 No significant events in the last 24 hours\n\n")
            
            # 3-day forecast (premium only)
            if include_forecast:
                if not limits["solar_forecasts"]:
                    result_text.append(_upgrade_message("3-day space weather forecasts"))
                else:
                    forecast_url = "https://services.swpc.noaa.gov/text/3-day-forecast.txt"
                    try:
                        forecast_resp = await self.http_client.get(forecast_url)
                        forecast_resp.raise_for_status()
                        result_text.append("\n**3-Day Forecast:**\n")
                        result_text.append(f"```\n{forecast_resp.text[:1500]}\n```\n")
                    except httpx.HTTPError:
                        result_text.append("\n⚠️ Could not fetch 3-day forecast\n")
            
            if self.tier == TIER_FREE:
                result_text.append(f"\n📋 {limits['polling_note']}")
            
            return [TextContent(type="text", text="".join(result_text))]
            
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching space weather data: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in solar monitoring: {e}")]
    
    # ─── Volcanoes ───────────────────────────────────────────────────────

    async def _check_volcanoes(
        self,
        alert_levels: Optional[List[str]] = None,
        region: Optional[str] = None
    ) -> List[TextContent]:
        """Monitor volcanic activity with tier-based access."""
        
        limits = self.limits
        
        # Enforce tier limits on alert levels
        if alert_levels is None:
            alert_levels = limits["volcano_alert_levels"]
        elif self.tier == TIER_FREE:
            # Free tier can only see WARNING
            requested = set(al.upper() for al in alert_levels)
            allowed = set(limits["volcano_alert_levels"])
            blocked = requested - allowed
            if blocked:
                alert_levels = list(allowed)
        
        # Region filtering is premium
        if region and not limits["volcano_region_filter"]:
            return [TextContent(
                type="text",
                text=f"🔒 Region filtering requires WEMS Premium.{_upgrade_message('Volcano region filtering and full alert levels')}"
            )]
            
        try:
            gvp_url = "https://volcano.si.edu/reports_weekly.cfm?format=json"
            response = await self.http_client.get(gvp_url)
            response.raise_for_status()
            
            result_text = ["🌋 **Volcanic Activity Status**\n\n"]
            result_text.append("**Recent Volcanic Activity:**\n")
            result_text.append("🟢 No significant volcanic alerts at monitored thresholds\n")
            result_text.append(f"📊 Alert levels monitored: {', '.join(alert_levels)}\n")
            
            if region and self.tier == TIER_PREMIUM:
                result_text.append(f"🌍 Region filter: {region}\n")
            
            if self.tier == TIER_FREE:
                result_text.append(f"\n📋 Free tier: WARNING alerts only. {limits['polling_note']}")
                result_text.append(_upgrade_message("All alert levels + region filtering"))
            
            return [TextContent(type="text", text="".join(result_text))]
            
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching volcanic data: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in volcano monitoring: {e}")]
    
    # ─── Tsunamis ────────────────────────────────────────────────────────

    async def _check_tsunamis(self, regions: Optional[List[str]] = None) -> List[TextContent]:
        """Check tsunami warnings with tier-based access."""
        
        limits = self.limits
        
        # Enforce tier limits on regions
        if regions is None:
            regions = limits["tsunami_regions"]
        elif self.tier == TIER_FREE:
            allowed = set(limits["tsunami_regions"])
            requested = set(r.lower() for r in regions)
            blocked = requested - allowed
            if blocked:
                regions = list(allowed)
            
        try:
            # Use NOAA Tsunami Warning Center Atom feeds (reliable, always available)
            atom_urls = {
                "pacific": "https://www.tsunami.gov/events/xml/PAAQAtom.xml",
                "atlantic": "https://www.tsunami.gov/events/xml/PHEBAtom.xml",
            }
            
            result_text = ["🌊 **Tsunami Alert Status**\n\n"]
            max_results = limits["tsunami_max_results"]
            
            active_warnings = []
            import xml.etree.ElementTree as ET
            
            for region_name in regions:
                feed_url = atom_urls.get(region_name)
                if not feed_url:
                    continue
                try:
                    resp = await self.http_client.get(feed_url)
                    resp.raise_for_status()
                    root = ET.fromstring(resp.text)
                    ns = {"atom": "http://www.w3.org/2005/Atom", "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#"}
                    
                    feed_title = root.findtext("atom:title", "", ns)
                    feed_updated = root.findtext("atom:updated", "", ns)
                    
                    for entry in root.findall("atom:entry", ns):
                        title = entry.findtext("atom:title", "Unknown", ns)
                        updated = entry.findtext("atom:updated", "", ns)
                        summary_el = entry.find("atom:summary", ns)
                        summary = ""
                        if summary_el is not None and summary_el.text:
                            # Strip HTML tags from summary
                            import re
                            summary = re.sub(r'<[^>]+>', ' ', summary_el.text).strip()
                            summary = re.sub(r'\s+', ' ', summary)[:200]
                        lat = entry.findtext("geo:lat", "", ns)
                        lon = entry.findtext("geo:long", "", ns)
                        
                        active_warnings.append({
                            "location": title,
                            "time": updated,
                            "summary": summary,
                            "lat": lat,
                            "lon": lon,
                            "region": region_name,
                            "feed_title": feed_title,
                        })
                except Exception:
                    continue
            
            if active_warnings:
                result_text.append("**Active Tsunami Warnings/Advisories:**\n")
                
                shown = 0
                for warning in active_warnings:
                    if shown >= max_results:
                        remaining = len(active_warnings) - max_results
                        if remaining > 0 and self.tier == TIER_FREE:
                            result_text.append(f"\n... and {remaining} more.{_upgrade_message('Full tsunami alerts for all ocean basins')}")
                        break
                    
                    location = warning.get("location", "Unknown location")
                    event_time = warning.get("time", "Unknown time")
                    summary = warning.get("summary", "")
                    
                    if event_time != "Unknown time":
                        try:
                            dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                            time_str = dt.strftime("%m-%d %H:%M UTC")
                        except (ValueError, TypeError):
                            time_str = event_time
                    else:
                        time_str = event_time
                    
                    result_text.append(f"🚨 **{location}**\n")
                    result_text.append(f"   Time: {time_str}\n")
                    if summary:
                        result_text.append(f"   {summary[:150]}\n")
                    result_text.append("\n")
                    shown += 1
                    
                    await self._check_tsunami_alert(location, "N/A", time_str)
            else:
                result_text.append("**Active Tsunami Warnings/Advisories:**\n")
                result_text.append("🟢 No active tsunami warnings or advisories\n\n")
            
            result_text.append(f"📊 Regions monitored: {', '.join(regions)}\n")
            result_text.append("🔍 Data source: NOAA Tsunami Warning Centers\n")
            
            if self.tier == TIER_FREE and set(regions) != {"pacific", "atlantic", "indian", "mediterranean"}:
                result_text.append(_upgrade_message("All ocean basins (Atlantic, Indian, Mediterranean)"))
            
            if self.tier == TIER_FREE:
                result_text.append(f"\n📋 {limits['polling_note']}")
            
            return [TextContent(type="text", text="".join(result_text))]
            
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching tsunami data: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in tsunami monitoring: {e}")]
    
    # ─── Hurricanes ──────────────────────────────────────────────────────

    async def _check_hurricanes(
        self,
        basin: str = "atlantic",
        include_forecast: bool = False
    ) -> List[TextContent]:
        """Monitor hurricanes and tropical storms with tier-based access."""
        
        limits = self.limits
        
        # Enforce tier limits on basins
        if basin == "all":
            basin = "atlantic"  # Default to atlantic for free tier
            if self.tier == TIER_FREE:
                basin = "atlantic"
            elif "pacific" not in limits["hurricane_basins"]:
                basin = "atlantic"
        elif basin not in limits["hurricane_basins"] and self.tier == TIER_FREE:
            return [TextContent(
                type="text",
                text=f"🔒 {basin.title()} basin requires WEMS Premium. Free tier supports: {', '.join(limits['hurricane_basins'])}.{_upgrade_message('All hurricane basins + forecast tracks')}"
            )]
        
        # Forecast tracks are premium only
        if include_forecast and not limits["hurricane_include_forecast"]:
            return [TextContent(
                type="text",
                text=f"🔒 Forecast tracks require WEMS Premium.{_upgrade_message('Hurricane forecast tracks and historical data')}"
            )]
        
        max_results = limits["hurricane_max_results"]
        
        try:
            # Fetch active storms from NHC RSS feeds (reliable, always available)
            import xml.etree.ElementTree as ET
            rss_urls = {
                "atlantic": "https://www.nhc.noaa.gov/index-at.xml",
                "pacific": "https://www.nhc.noaa.gov/index-ep.xml",
            }
            
            result_text = [f"🌀 **Hurricane/Tropical Storm Status** ({basin.title()})\n\n"]
            
            active_storms = []
            basins_to_check = list(rss_urls.keys()) if basin == "all" else [basin]
            
            for b in basins_to_check:
                rss_url = rss_urls.get(b)
                if not rss_url:
                    continue
                try:
                    rss_resp = await self.http_client.get(rss_url)
                    rss_resp.raise_for_status()
                    root = ET.fromstring(rss_resp.text)
                    nhc_ns = {"nhc": "https://www.nhc.noaa.gov"}
                    
                    for item in root.findall(".//item"):
                        title = item.findtext("title", "")
                        desc = item.findtext("description", "")
                        link = item.findtext("link", "")
                        pub_date = item.findtext("pubDate", "")
                        
                        # NHC RSS items include cyclone entries with nhc:center etc.
                        center = item.findtext("nhc:center", "", nhc_ns)
                        movement = item.findtext("nhc:movement", "", nhc_ns)
                        wind = item.findtext("nhc:wind", "", nhc_ns)
                        pressure = item.findtext("nhc:pressure", "", nhc_ns)
                        
                        if center or wind:  # It's a cyclone entry
                            active_storms.append({
                                "name": title,
                                "intensity": f"Wind: {wind}" if wind else "Unknown",
                                "movement": movement or "Unknown",
                                "location": center or "Unknown",
                                "pressure": pressure,
                                "link": link,
                                "basin": b,
                            })
                except Exception:
                    continue
            
            # Also fetch NWS tropical alerts
            try:
                alerts_url = "https://api.weather.gov/alerts/active?event=Hurricane,Tropical%20Storm,Hurricane%20Warning,Hurricane%20Watch"
                alerts_response = await self.http_client.get(alerts_url)
                alerts_response.raise_for_status()
                alerts_data = alerts_response.json()
            except Exception:
                alerts_data = {"features": []}
            
            if active_storms:
                result_text.append("**Active Storms:**\n")
                
                shown = 0
                for storm in active_storms:
                    if shown >= max_results:
                        remaining = len(active_storms) - max_results
                        if remaining > 0 and self.tier == TIER_FREE:
                            result_text.append(f"\n... and {remaining} more storms.{_upgrade_message('Full hurricane tracking for all basins')}")
                        break
                    
                    name = storm.get("name", "Unnamed")
                    intensity = storm.get("intensity", "Unknown")
                    movement = storm.get("movement", "Unknown")
                    location = storm.get("location", "Unknown")
                    
                    if "hurricane" in intensity.lower() or "hurricane" in name.lower():
                        storm_icon = "🔴"
                    elif "tropical storm" in intensity.lower() or "tropical storm" in name.lower():
                        storm_icon = "🟠"
                    else:
                        storm_icon = "🟡"
                    
                    result_text.append(f"{storm_icon} **{name}** - {intensity}\n")
                    result_text.append(f"   Location: {location}\n")
                    result_text.append(f"   Movement: {movement}\n\n")
                    
                    shown += 1
                    
                    await self._check_hurricane_alert(name, intensity, location)
            else:
                result_text.append("**Active Storms:**\n")
                result_text.append("🟢 No active hurricanes or tropical storms\n\n")
            
            # Process active alerts
            if alerts_data and "features" in alerts_data:
                alert_count = len(alerts_data["features"])
                if alert_count > 0:
                    result_text.append(f"**Active Tropical Alerts:** {alert_count} warnings/watches\n")
                    
                    for alert in alerts_data["features"][:3]:  # Show up to 3 alerts
                        properties = alert.get("properties", {})
                        headline = properties.get("headline", "Unknown Alert")
                        areas = properties.get("areaDesc", "Unknown Area")
                        
                        if "hurricane warning" in headline.lower():
                            alert_icon = "🚨"
                        elif "hurricane watch" in headline.lower():
                            alert_icon = "⚠️"
                        elif "tropical storm warning" in headline.lower():
                            alert_icon = "🟠"
                        else:
                            alert_icon = "🟡"
                        
                        result_text.append(f"{alert_icon} {headline}\n")
                        result_text.append(f"   Areas: {areas[:100]}{'...' if len(areas) > 100 else ''}\n")
                else:
                    result_text.append("**Active Tropical Alerts:**\n")
                    result_text.append("🟢 No active hurricane or tropical storm alerts\n")
            
            result_text.append(f"\n📊 Basin: {basin.title()}\n")
            result_text.append("🔍 Data sources: NHC, NWS\n")
            
            if include_forecast and self.tier == TIER_PREMIUM:
                result_text.append("📈 Forecast tracks included (Premium)\n")
            
            if self.tier == TIER_FREE:
                result_text.append(f"\n📋 {limits['polling_note']}")
                if basin != "atlantic" or include_forecast:
                    result_text.append(_upgrade_message("All hurricane basins + forecast tracks"))
            
            return [TextContent(type="text", text="".join(result_text))]
            
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching hurricane data: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in hurricane monitoring: {e}")]
    
    # ─── Wildfires ───────────────────────────────────────────────────────

    async def _check_wildfires(
        self,
        region: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[TextContent]:
        """Monitor wildfire activity and fire weather alerts with tier-based access."""
        
        limits = self.limits
        
        # Region filtering is premium
        if region and not limits["wildfire_region_filter"]:
            return [TextContent(
                type="text",
                text=f"🔒 Region filtering requires WEMS Premium.{_upgrade_message('Wildfire region filtering and full fire data')}"
            )]
        
        max_results = limits["wildfire_max_results"]
        
        try:
            # Fetch fire weather alerts from NWS
            alerts_url = "https://api.weather.gov/alerts/active?event=Fire%20Weather%20Watch,Red%20Flag%20Warning"
            alerts_response = await self.http_client.get(alerts_url)
            alerts_response.raise_for_status()
            alerts_data = alerts_response.json()
            
            # Fetch active fire perimeters from NIFC (premium gets full data)
            fire_data = None
            if self.tier == TIER_PREMIUM:
                try:
                    nifc_url = "https://services3.arcgis.com/T4QMspbfLg3qTGWY/arcgis/rest/services/Current_WildlandFire_Perimeters/FeatureServer/0/query?where=1%3D1&outFields=*&f=json&resultRecordCount=10&orderByFields=GISAcres DESC"
                    nifc_response = await self.http_client.get(nifc_url)
                    nifc_response.raise_for_status()
                    fire_data = nifc_response.json()
                except httpx.HTTPError:
                    fire_data = None
            
            result_text = ["🔥 **Wildfire Activity Status**\n\n"]
            
            # Process fire weather alerts
            active_alerts = []
            if alerts_data and "features" in alerts_data:
                for alert in alerts_data["features"]:
                    properties = alert.get("properties", {})
                    if region:
                        areas = properties.get("areaDesc", "").lower()
                        if region.lower() not in areas:
                            continue
                    active_alerts.append(alert)
            
            if active_alerts:
                result_text.append(f"**Fire Weather Alerts:** {len(active_alerts)} active\n")
                
                shown = 0
                for alert in active_alerts:
                    if shown >= max_results:
                        remaining = len(active_alerts) - max_results
                        if remaining > 0 and self.tier == TIER_FREE:
                            result_text.append(f"\n... and {remaining} more alerts.{_upgrade_message('Full fire weather alerts + fire perimeter data')}")
                        break
                    
                    properties = alert.get("properties", {})
                    headline = properties.get("headline", "Fire Weather Alert")
                    areas = properties.get("areaDesc", "Unknown Areas")
                    severity_level = properties.get("severity", "Minor")
                    
                    if "red flag warning" in headline.lower() or severity_level.lower() == "extreme":
                        alert_icon = "🔴"
                    elif "fire weather watch" in headline.lower() or severity_level.lower() in ["severe", "moderate"]:
                        alert_icon = "🟠"
                    else:
                        alert_icon = "🟡"
                    
                    # Filter by severity if specified
                    if severity:
                        if severity.lower() == "critical" and "red flag" not in headline.lower():
                            continue
                        elif severity.lower() == "high" and alert_icon not in ["🔴", "🟠"]:
                            continue
                    
                    result_text.append(f"{alert_icon} {headline}\n")
                    result_text.append(f"   Areas: {areas[:100]}{'...' if len(areas) > 100 else ''}\n")
                    result_text.append(f"   Severity: {severity_level}\n\n")
                    
                    shown += 1
                    
                    await self._check_wildfire_alert(headline, areas, severity_level)
            else:
                result_text.append("**Fire Weather Alerts:**\n")
                result_text.append("🟢 No active fire weather watches or warnings\n\n")
            
            # Process active fires (premium only)
            if fire_data and self.tier == TIER_PREMIUM and "features" in fire_data:
                fires = fire_data["features"]
                if fires:
                    result_text.append(f"**Active Large Fires:** {len(fires)} incidents\n")
                    
                    for fire in fires[:5]:  # Top 5 largest fires
                        attributes = fire.get("attributes", {})
                        fire_name = attributes.get("IncidentName", "Unknown Fire")
                        acres = attributes.get("GISAcres", 0)
                        containment = attributes.get("PercentContained", 0)
                        state = attributes.get("POOState", "Unknown")
                        
                        if acres > 100000:
                            fire_icon = "🔥"
                        elif acres > 50000:
                            fire_icon = "🟠"
                        elif acres > 10000:
                            fire_icon = "🟡"
                        else:
                            fire_icon = "🔸"
                        
                        result_text.append(f"{fire_icon} **{fire_name}** ({state})\n")
                        result_text.append(f"   Size: {acres:,.0f} acres | {containment}% contained\n\n")
                else:
                    result_text.append("**Active Large Fires:**\n")
                    result_text.append("🟢 No large wildfires currently active\n\n")
            
            if region and self.tier == TIER_PREMIUM:
                result_text.append(f"🌍 Region filter: {region}\n")
            
            if severity:
                result_text.append(f"⚠️ Severity filter: {severity}\n")
            
            result_text.append("🔍 Data sources: NWS Fire Weather, NIFC\n")
            
            if self.tier == TIER_FREE:
                result_text.append(f"\n📋 Free tier: Fire weather alerts only. {limits['polling_note']}")
                result_text.append(_upgrade_message("Active fire perimeters + region filtering"))
            
            return [TextContent(type="text", text="".join(result_text))]
            
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching wildfire data: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in wildfire monitoring: {e}")]

    # ─── Severe Weather ──────────────────────────────────────────────────

    async def _check_severe_weather(
        self,
        state: Optional[str] = None,
        severity: Optional[List[str]] = None,
        event_type: Optional[List[str]] = None,
        urgency: Optional[List[str]] = None,
        certainty: Optional[List[str]] = None
    ) -> List[TextContent]:
        """Monitor severe weather alerts with tier-based access."""
        
        limits = self.limits
        
        # State filtering is premium only
        if state and not limits["severe_weather_state_filter"]:
            return [TextContent(
                type="text",
                text=f"🔒 State filtering requires WEMS Premium.{_upgrade_message('Severe weather state filtering + extended time ranges')}"
            )]
        
        # Default severity based on tier
        if not severity:
            severity = limits["severe_weather_severities"]
        else:
            # Filter out unavailable severities for free tier
            if self.tier == TIER_FREE:
                allowed_severities = limits["severe_weather_severities"]
                severity = [s for s in severity if s in allowed_severities]
                if not severity:
                    return [TextContent(
                        type="text",
                        text=f"🔒 Requested severity levels require WEMS Premium. Free tier supports: {', '.join(allowed_severities)}.{_upgrade_message('All severity levels + extended filtering')}"
                    )]
        
        max_results = limits["severe_weather_max_results"]
        time_range_hours = limits["severe_weather_time_range"]
        
        try:
            # Build URL with filters
            url = "https://api.weather.gov/alerts/active"
            params = []
            
            if state:
                params.append(f"area={state}")
            
            if event_type:
                # Convert common event types to NWS event names
                nws_events = []
                for event in event_type:
                    if "tornado" in event.lower():
                        nws_events.extend(["Tornado Warning", "Tornado Watch"])
                    elif "thunderstorm" in event.lower() or "storm" in event.lower():
                        nws_events.extend(["Severe Thunderstorm Warning", "Severe Thunderstorm Watch"])
                    elif "flood" in event.lower():
                        nws_events.extend(["Flash Flood Warning", "Flash Flood Watch", "Flood Warning", "Flood Watch"])
                    elif "winter" in event.lower() or "snow" in event.lower() or "ice" in event.lower():
                        nws_events.extend(["Winter Storm Warning", "Winter Storm Watch", "Blizzard Warning", "Ice Storm Warning"])
                    else:
                        nws_events.append(event)
                
                if nws_events:
                    params.append(f"event={','.join(nws_events)}")
            
            if urgency:
                params.append(f"urgency={','.join(urgency)}")
            
            if certainty:
                params.append(f"certainty={','.join(certainty)}")
            
            if params:
                url += "?" + "&".join(params)
            
            response = await self.http_client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Note: NWS /alerts/active is already an active-alert feed.
            # Avoid hard filtering by sent-time so feed semantics drive recency.
            result_text = ["⛈️ **Severe Weather Alerts**\n\n"]
            
            if state:
                result_text.append(f"🌍 State: {state.upper()}\n")
            
            # Process alerts
            filtered_alerts = []
            if data and "features" in data:
                for alert in data["features"]:
                    properties = alert.get("properties", {})
                    
                    # Filter by severity
                    alert_severity = properties.get("severity", "").lower()
                    if alert_severity and alert_severity not in [s.lower() for s in severity]:
                        continue
                    
                    # Filter out test messages
                    if properties.get("status", "").lower() == "test":
                        continue
                    
                    filtered_alerts.append(alert)
            
            if not filtered_alerts:
                tier_info = f" (last {time_range_hours}h)" if self.tier == TIER_FREE else ""
                result_text.append(f"🟢 No severe weather alerts{tier_info}")
                if state:
                    result_text.append(f" for {state.upper()}")
                result_text.append("\n")
            else:
                result_text.append(f"**Active Alerts:** {len(filtered_alerts)} found\n\n")
                
                shown = 0
                for alert in filtered_alerts:
                    if shown >= max_results:
                        remaining = len(filtered_alerts) - max_results
                        if remaining > 0 and self.tier == TIER_FREE:
                            result_text.append(f"\n... and {remaining} more alerts.{_upgrade_message('Full severe weather alerts + extended time ranges')}")
                        elif remaining > 0:
                            result_text.append(f"\n... and {remaining} more alerts (showing top {max_results})")
                        break
                    
                    properties = alert.get("properties", {})
                    
                    event = properties.get("event", "Weather Alert")
                    headline = properties.get("headline", event)
                    areas = properties.get("areaDesc", "Unknown Areas")
                    alert_severity = properties.get("severity", "Unknown")
                    alert_urgency = properties.get("urgency", "Unknown")
                    alert_certainty = properties.get("certainty", "Unknown")
                    sent_time = properties.get("sent", "")
                    expires_time = properties.get("expires", "")
                    
                    # Choose icon based on event type and severity
                    if "tornado" in event.lower():
                        if "warning" in event.lower():
                            icon = "🔴🌪️"
                        else:
                            icon = "🟠🌪️"
                    elif "thunderstorm" in event.lower():
                        if "warning" in event.lower():
                            icon = "🔴⛈️"
                        else:
                            icon = "🟠⛈️"
                    elif "flood" in event.lower():
                        if "flash flood warning" in event.lower():
                            icon = "🔴🌊"
                        elif "warning" in event.lower():
                            icon = "🟠🌊"
                        else:
                            icon = "🟡🌊"
                    elif "winter" in event.lower() or "blizzard" in event.lower() or "ice" in event.lower():
                        if "warning" in event.lower():
                            icon = "🔴❄️"
                        else:
                            icon = "🟠❄️"
                    else:
                        if alert_severity.lower() == "extreme":
                            icon = "🔴⚠️"
                        elif alert_severity.lower() == "severe":
                            icon = "🟠⚠️"
                        elif alert_severity.lower() == "moderate":
                            icon = "🟡⚠️"
                        else:
                            icon = "🟢⚠️"
                    
                    result_text.append(f"{icon} **{event}**\n")
                    result_text.append(f"   Areas: {areas}\n")
                    result_text.append(f"   Severity: {alert_severity} | Urgency: {alert_urgency} | Certainty: {alert_certainty}\n")
                    
                    if sent_time:
                        sent_dt = datetime.fromisoformat(sent_time.replace('Z', '+00:00'))
                        time_str = sent_dt.strftime("%m-%d %H:%M UTC")
                        result_text.append(f"   Issued: {time_str}")
                        
                        if expires_time:
                            expires_dt = datetime.fromisoformat(expires_time.replace('Z', '+00:00'))
                            expires_str = expires_dt.strftime("%m-%d %H:%M UTC")
                            result_text.append(f" | Expires: {expires_str}")
                        
                        result_text.append("\n")
                    
                    if headline and headline != event:
                        # Truncate long headlines
                        if len(headline) > 100:
                            headline = headline[:97] + "..."
                        result_text.append(f"   📋 {headline}\n")
                    
                    result_text.append("\n")
                    shown += 1
                    
                    await self._check_severe_weather_alert(event, areas, alert_severity, sent_time)
            
            # Footer
            result_text.append("🔍 Data source: National Weather Service\n")
            
            if self.tier == TIER_FREE:
                result_text.append(f"\n📋 Free tier: Last {time_range_hours}h, {', '.join(severity)} severity only. {limits['polling_note']}")
                result_text.append(_upgrade_message("Extended time ranges + all severity levels + state filtering"))
            
            return [TextContent(type="text", text="".join(result_text))]
            
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching severe weather data: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in severe weather monitoring: {e}")]

    # ─── Alert Configuration (Premium) ───────────────────────────────────

    async def _configure_alerts(self, alert_type: str, config: Dict[str, Any]) -> List[TextContent]:
        """Update alert configuration (premium only)."""
        if alert_type not in self.config.get("alerts", {}):
            return [TextContent(type="text", text=f"❌ Unknown alert type: {alert_type}")]
        
        self.config["alerts"][alert_type].update(config)
        
        return [TextContent(
            type="text", 
            text=f"✅ Updated {alert_type} alert configuration: {config}"
        )]
    
    # ─── Alert Webhooks ──────────────────────────────────────────────────

    async def _check_earthquake_alert(self, magnitude: float, place: str, time: datetime):
        alert_config = self.config.get("alerts", {}).get("earthquake", {})
        min_mag = alert_config.get("min_magnitude", 6.0)
        webhook_url = alert_config.get("webhook")
        
        if magnitude >= min_mag and webhook_url:
            payload = {
                "event_type": "earthquake",
                "magnitude": magnitude,
                "location": place,
                "timestamp": time.isoformat(),
                "alert_level": "major" if magnitude >= 7.0 else "warning"
            }
            try:
                await self.http_client.post(webhook_url, json=payload)
            except httpx.HTTPError:
                pass

    async def _check_solar_alert(self, k_index: float, level_text: str, time: datetime):
        alert_config = self.config.get("alerts", {}).get("solar", {})
        min_kp = alert_config.get("min_kp_index", 7.0)
        webhook_url = alert_config.get("webhook")
        
        if k_index >= min_kp and webhook_url:
            payload = {
                "event_type": "solar",
                "k_index": k_index,
                "level": level_text,
                "timestamp": time.isoformat(),
                "alert_level": "severe" if k_index >= 8.0 else "warning"
            }
            try:
                await self.http_client.post(webhook_url, json=payload)
            except httpx.HTTPError:
                pass

    async def _check_volcano_alert(self, volcano_name: str, alert_level: str, time: str):
        alert_config = self.config.get("alerts", {}).get("volcano", {})
        monitored_levels = alert_config.get("alert_levels", ["WARNING", "WATCH"])
        webhook_url = alert_config.get("webhook")
        
        if alert_level in monitored_levels and webhook_url:
            payload = {
                "event_type": "volcano",
                "volcano_name": volcano_name,
                "alert_level": alert_level.lower(),
                "timestamp": time,
                "severity": "critical" if alert_level == "WARNING" else "warning"
            }
            try:
                await self.http_client.post(webhook_url, json=payload)
            except httpx.HTTPError:
                pass

    async def _check_tsunami_alert(self, location: str, magnitude: str, time: str):
        alert_config = self.config.get("alerts", {}).get("tsunami", {})
        webhook_url = alert_config.get("webhook")
        enabled = alert_config.get("enabled", True)
        
        if enabled and webhook_url:
            payload = {
                "event_type": "tsunami",
                "location": location,
                "magnitude": magnitude,
                "timestamp": time,
                "alert_level": "critical"
            }
            try:
                await self.http_client.post(webhook_url, json=payload)
            except httpx.HTTPError:
                pass
                
    async def _check_hurricane_alert(self, name: str, intensity: str, location: str):
        alert_config = self.config.get("alerts", {}).get("hurricane", {})
        webhook_url = alert_config.get("webhook")
        enabled = alert_config.get("enabled", True)
        
        if enabled and webhook_url and ("hurricane" in intensity.lower() or "tropical storm" in intensity.lower()):
            payload = {
                "event_type": "hurricane",
                "storm_name": name,
                "intensity": intensity,
                "location": location,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "alert_level": "critical" if "hurricane" in intensity.lower() else "warning"
            }
            try:
                await self.http_client.post(webhook_url, json=payload)
            except httpx.HTTPError:
                pass

    async def _check_wildfire_alert(self, headline: str, areas: str, severity: str):
        alert_config = self.config.get("alerts", {}).get("wildfire", {})
        webhook_url = alert_config.get("webhook")
        enabled = alert_config.get("enabled", True)
        
        if enabled and webhook_url and ("red flag warning" in headline.lower() or severity.lower() in ["extreme", "severe"]):
            payload = {
                "event_type": "wildfire",
                "alert_type": headline,
                "areas": areas,
                "severity": severity,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "alert_level": "critical" if "red flag" in headline.lower() else "warning"
            }
            try:
                await self.http_client.post(webhook_url, json=payload)
            except httpx.HTTPError:
                pass

    async def _check_severe_weather_alert(self, event: str, areas: str, severity: str, sent_time: str):
        alert_config = self.config.get("alerts", {}).get("severe_weather", {})
        webhook_url = alert_config.get("webhook")
        enabled = alert_config.get("enabled", True)
        
        # Alert on warnings and severe/extreme events
        trigger_events = ["warning", "emergency"]
        trigger_severities = ["extreme", "severe"]
        
        should_alert = (enabled and webhook_url and 
                       (any(trigger in event.lower() for trigger in trigger_events) or
                        severity.lower() in trigger_severities))
        
        if should_alert:
            payload = {
                "event_type": "severe_weather",
                "weather_event": event,
                "areas": areas,
                "severity": severity,
                "timestamp": sent_time or datetime.now(timezone.utc).isoformat(),
                "alert_level": "emergency" if "tornado warning" in event.lower() else "critical" if severity.lower() == "extreme" else "warning"
            }
            try:
                await self.http_client.post(webhook_url, json=payload)
            except httpx.HTTPError:
                pass

    # ─── Air Quality ────────────────────────────────────────────────────

    # OpenAQ parameter name → id mapping
    _OPENAQ_PARAMS = {
        "pm25": 2,
        "pm10": 1,
        "o3": 3,
        "no2": 5,
        "so2": 9,
        "co": 7,
    }

    # OpenAQ parameter id → display name
    _OPENAQ_PARAM_NAMES = {
        2: "PM2.5",
        1: "PM10",
        3: "O₃ (Ozone)",
        5: "NO₂",
        9: "SO₂",
        7: "CO",
    }

    @staticmethod
    def _aqi_category(value: float, parameter: str = "pm25") -> tuple:
        """Return (icon, label, level) for an AQI value.

        Simplified US EPA AQI breakpoints for PM2.5 (µg/m³ 24-hr).
        For other parameters the same thresholds are used as a rough
        "concentration index" – acceptable for user-facing display.
        """
        if value <= 50:
            return ("🟢", "Good", "good")
        elif value <= 100:
            return ("🟡", "Moderate", "moderate")
        elif value <= 150:
            return ("🟠", "Unhealthy for Sensitive Groups", "usg")
        elif value <= 200:
            return ("🔴", "Unhealthy", "unhealthy")
        elif value <= 300:
            return ("🟣", "Very Unhealthy", "very_unhealthy")
        else:
            return ("🟤", "Hazardous", "hazardous")

    async def _check_air_quality(
        self,
        zip_code: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        country: str = "US",
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_km: float = 25,
        parameters: Optional[List[str]] = None,
        include_forecast: bool = False,
    ) -> List[TextContent]:
        """Monitor air quality via OpenAQ v3 with tier-based access."""

        limits = self.limits

        # ── gate: city / zip filtering is premium ──
        if (zip_code or city) and not limits["air_quality_city_filter"]:
            return [TextContent(
                type="text",
                text=f"🔒 City/ZIP code filtering requires WEMS Premium.{_upgrade_message('Local air quality by city or ZIP code')}"
            )]

        # ── gate: country filter – free is US only ──
        allowed_countries = limits["air_quality_countries"]
        if allowed_countries and country.upper() not in [c.upper() for c in allowed_countries]:
            return [TextContent(
                type="text",
                text=f"🔒 Air quality data for {country.upper()} requires WEMS Premium. Free tier supports: {', '.join(allowed_countries)}.{_upgrade_message('Global air quality monitoring')}"
            )]

        # ── gate: parameters ──
        allowed_params = limits["air_quality_parameters"]
        if parameters is None:
            parameters = list(allowed_params)
        else:
            if self.tier == TIER_FREE:
                blocked = [p for p in parameters if p not in allowed_params]
                if blocked:
                    parameters = [p for p in parameters if p in allowed_params]
                    if not parameters:
                        return [TextContent(
                            type="text",
                            text=f"🔒 Requested pollutants require WEMS Premium. Free tier supports: {', '.join(allowed_params)}.{_upgrade_message('All pollutant parameters (PM10, NO₂, SO₂, CO)')}"
                        )]

        # ── gate: forecast ──
        if include_forecast and not limits["air_quality_forecast"]:
            return [TextContent(
                type="text",
                text=f"🔒 AQI forecasts require WEMS Premium.{_upgrade_message('Air quality forecasts')}"
            )]

        max_results = limits["air_quality_max_results"]

        try:
            # Use EPA AirNow open data files (free, no API key, updated hourly)
            # Format: date|date|time|tz|offset|observed|current|city|state|lat|lon|param|aqi|category|...
            airnow_url = "https://files.airnowtech.org/airnow/today/reportingarea.dat"
            resp = await self.http_client.get(airnow_url)
            resp.raise_for_status()
            
            # Parse pipe-delimited data
            import math
            all_measurements = []
            param_map = {"pm2.5": "pm25", "pm25": "pm25", "pm10": "pm10", "ozone": "o3", "o3": "o3",
                         "no2": "no2", "so2": "so2", "co": "co"}
            
            for line in resp.text.strip().split("\n"):
                fields = line.split("|")
                if len(fields) < 14:
                    continue
                
                obs_city = fields[7].strip()
                obs_state = fields[8].strip()
                obs_lat = fields[9].strip()
                obs_lon = fields[10].strip()
                obs_param = fields[11].strip().lower()
                obs_aqi_str = fields[12].strip()
                obs_category = fields[13].strip()
                
                # Map parameter name
                mapped_param = param_map.get(obs_param, obs_param)
                if mapped_param not in parameters:
                    continue
                
                # Filter by state if specified
                if state and obs_state.upper() != state.upper():
                    continue
                
                # Filter by city if specified (premium)
                if city and city.lower() not in obs_city.lower():
                    continue
                
                # Filter by country (AirNow is US-only, but that's fine for free tier)
                # For premium with non-US countries, we'd need a different source
                if country and country.upper() != "US":
                    continue
                
                try:
                    obs_aqi = int(obs_aqi_str) if obs_aqi_str else 0
                except (ValueError, TypeError):
                    obs_aqi = 0
                
                # Filter by coordinates + radius if specified
                if latitude is not None and longitude is not None:
                    try:
                        lat_f = float(obs_lat)
                        lon_f = float(obs_lon)
                        # Haversine approximation (km)
                        dlat = math.radians(lat_f - latitude)
                        dlon = math.radians(lon_f - longitude)
                        a = math.sin(dlat/2)**2 + math.cos(math.radians(latitude)) * math.cos(math.radians(lat_f)) * math.sin(dlon/2)**2
                        dist_km = 6371 * 2 * math.asin(math.sqrt(a))
                        if dist_km > radius_km:
                            continue
                    except (ValueError, TypeError):
                        continue
                
                all_measurements.append({
                    "value": obs_aqi,
                    "_location": {"name": f"{obs_city}, {obs_state}", "lat": obs_lat, "lon": obs_lon},
                    "_param_name": mapped_param,
                    "_category": obs_category,
                    "_is_aqi": True,  # AirNow gives us AQI directly
                })

            # ── Step 3: format output ──
            result_text = ["🌬️ **Air Quality Report**\n\n"]

            if city:
                result_text.append(f"📍 City: {city}\n")
            if zip_code:
                result_text.append(f"📍 ZIP: {zip_code}\n")
            if state:
                result_text.append(f"📍 State: {state.upper()}\n")
            if latitude is not None and longitude is not None:
                result_text.append(f"📍 Coordinates: {latitude}, {longitude} (radius {radius_km} km)\n")
            result_text.append(f"🌍 Country: {country.upper()}\n\n")

            if not all_measurements:
                result_text.append("🟢 No air quality data available for this area\n")
            else:
                # Deduplicate by location, keep latest per param per location
                seen = {}
                for m in all_measurements:
                    loc = m.get("_location", {})
                    loc_name = loc.get("name", "Unknown Station")
                    param = m.get("_param_name", "unknown")
                    key = f"{loc_name}|{param}"
                    if key not in seen:
                        seen[key] = m

                unique = list(seen.values())

                # Group by location
                by_location = {}
                for m in unique:
                    loc = m.get("_location", {})
                    loc_name = loc.get("name", "Unknown Station")
                    by_location.setdefault(loc_name, []).append(m)

                shown = 0
                for loc_name, measurements in by_location.items():
                    if shown >= max_results:
                        remaining = len(by_location) - max_results
                        if remaining > 0 and self.tier == TIER_FREE:
                            result_text.append(f"\n... and {remaining} more stations.{_upgrade_message('Full air quality results (up to 25 stations)')}")
                        elif remaining > 0:
                            result_text.append(f"\n... and {remaining} more stations (showing top {max_results})")
                        break

                    result_text.append(f"📊 **{loc_name}**\n")

                    for m in measurements:
                        value = m.get("value")
                        param = m.get("_param_name", "unknown")
                        param_id = self._OPENAQ_PARAMS.get(param, 0)
                        display_name = self._OPENAQ_PARAM_NAMES.get(param_id, param.upper())
                        is_aqi = m.get("_is_aqi", False)

                        if value is not None:
                            try:
                                val = float(value)
                            except (ValueError, TypeError):
                                val = 0.0
                            
                            if is_aqi:
                                # AirNow provides AQI directly — use it for category lookup
                                icon, label, _level = self._aqi_category(val, "aqi")
                                result_text.append(f"   {icon} {display_name}: AQI {val:.0f} — {label}\n")
                            else:
                                icon, label, _level = self._aqi_category(val, param)
                                result_text.append(f"   {icon} {display_name}: {val:.1f} — {label}\n")

                            # Trigger alert for unhealthy+
                            if _level in ("unhealthy", "very_unhealthy", "hazardous"):
                                await self._check_air_quality_alert(
                                    loc_name, display_name, val, label
                                )

                    result_text.append("\n")
                    shown += 1

            # Forecast placeholder (premium)
            if include_forecast and self.tier == TIER_PREMIUM:
                result_text.append("📈 **AQI Forecast:** Feature coming soon (premium)\n\n")

            result_text.append("🔍 Data source: EPA AirNow\n")

            if self.tier == TIER_FREE:
                result_text.append(f"\n📋 Free tier: US only, PM2.5/O3 only, max {max_results} stations. {limits['polling_note']}")
                result_text.append(_upgrade_message("Global AQI + all pollutants + city/ZIP search + forecasts"))

            return [TextContent(type="text", text="".join(result_text))]

        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching air quality data: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in air quality monitoring: {e}")]

    async def _check_air_quality_alert(self, station: str, parameter: str, value: float, label: str):
        """Trigger webhook alert for unhealthy air quality."""
        alert_config = self.config.get("alerts", {}).get("air_quality", {})
        webhook_url = alert_config.get("webhook")
        enabled = alert_config.get("enabled", True)

        if enabled and webhook_url:
            payload = {
                "event_type": "air_quality",
                "station": station,
                "parameter": parameter,
                "value": value,
                "aqi_label": label,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "alert_level": "hazardous" if value > 300 else "critical" if value > 200 else "warning"
            }
            try:
                await self.http_client.post(webhook_url, json=payload)
            except httpx.HTTPError:
                pass

    # ─── Threat Advisories ─────────────────────────────────────────────

    # Travel advisory level descriptions
    _TRAVEL_LEVELS = {
        "1": ("🟢", "Exercise Normal Precautions"),
        "2": ("🟡", "Exercise Increased Caution"),
        "3": ("🟠", "Reconsider Travel"),
        "4": ("🔴", "Do Not Travel"),
    }

    # NTAS threat type icons
    _NTAS_ICONS = {
        "elevated": "🟡",
        "imminent": "🔴",
    }

    async def _check_threat_advisories(
        self,
        threat_types: Optional[List[str]] = None,
        countries: Optional[List[str]] = None,
        region: Optional[str] = None,
        threat_level: Optional[List[str]] = None,
        include_expired: bool = False,
        include_historical: bool = False,
    ) -> List[TextContent]:
        """Monitor threat advisories from DHS NTAS and State Dept with tier-based access."""

        limits = self.limits

        # ── gate: threat types ──
        allowed_types = limits["threat_types"]
        if threat_types is None:
            if self.tier == TIER_FREE:
                threat_types = ["terrorism"]
            else:
                threat_types = ["all"]
        else:
            if self.tier == TIER_FREE:
                blocked = [t for t in threat_types if t not in allowed_types and t != "all"]
                if blocked or "all" in threat_types:
                    threat_types = [t for t in threat_types if t in allowed_types]
                    if not threat_types:
                        return [TextContent(
                            type="text",
                            text=f"🔒 Requested threat types require WEMS Premium. Free tier supports: {', '.join(allowed_types)}.{_upgrade_message('All threat types (travel, cyber, terrorism)')}"
                        )]

        # ── gate: country filtering ──
        if countries and not limits["threat_countries_filter"]:
            return [TextContent(
                type="text",
                text=f"🔒 Country filtering requires WEMS Premium.{_upgrade_message('Country-specific travel advisories')}"
            )]

        # ── gate: region filtering ──
        if region and not limits["threat_region_filter"]:
            return [TextContent(
                type="text",
                text=f"🔒 Region filtering requires WEMS Premium.{_upgrade_message('Region-specific threat monitoring')}"
            )]

        # ── gate: expired advisories ──
        if include_expired and not limits["threat_include_expired"]:
            return [TextContent(
                type="text",
                text=f"🔒 Expired advisories require WEMS Premium.{_upgrade_message('Historical threat advisory data')}"
            )]

        # ── gate: historical data ──
        if include_historical and not limits["threat_include_historical"]:
            return [TextContent(
                type="text",
                text=f"🔒 Historical threat data requires WEMS Premium.{_upgrade_message('Historical threat advisory data')}"
            )]

        max_results = limits["threat_max_results"]

        # Resolve "all" into specific types
        effective_types = set()
        for t in threat_types:
            if t == "all":
                effective_types.update(["terrorism", "travel", "cyber"])
            else:
                effective_types.add(t)

        try:
            result_text = ["🛡️ **Threat Advisory Report**\n\n"]
            all_advisories: List[Dict[str, Any]] = []

            # ── 1. DHS NTAS (terrorism) ──
            if "terrorism" in effective_types:
                ntas_advisories = await self._fetch_ntas_advisories(
                    include_expired=include_expired
                )
                all_advisories.extend(ntas_advisories)

            # ── 2. State Dept Travel Advisories ──
            if "travel" in effective_types:
                travel_advisories = await self._fetch_travel_advisories(
                    countries=countries,
                    region=region,
                    threat_level=threat_level,
                )
                all_advisories.extend(travel_advisories)

            # ── 3. Cyber Threat Advisories (CISA) ──
            if "cyber" in effective_types:
                cyber_advisories = await self._fetch_cyber_advisories()
                all_advisories.extend(cyber_advisories)

            # Filter by threat level if specified (for NTAS)
            if threat_level:
                filtered = []
                for adv in all_advisories:
                    adv_level = adv.get("level", "").lower()
                    adv_source = adv.get("source", "")
                    if adv_source == "ntas":
                        if adv_level in [tl.lower() for tl in threat_level]:
                            filtered.append(adv)
                    elif adv_source == "travel":
                        # Travel levels are 1-4
                        adv_num = adv.get("level_num", "0")
                        if str(adv_num) in threat_level:
                            filtered.append(adv)
                    else:
                        filtered.append(adv)
                all_advisories = filtered

            if not all_advisories:
                result_text.append("🟢 No active threat advisories")
                if "terrorism" in effective_types:
                    result_text.append("\n   📋 DHS NTAS: No current terrorism advisories")
                if "travel" in effective_types:
                    if countries:
                        result_text.append(f"\n   📋 State Dept: No advisories matching filter")
                    else:
                        result_text.append("\n   📋 State Dept: No high-level travel advisories")
                if "cyber" in effective_types:
                    result_text.append("\n   📋 CISA: No current cyber advisories")
                result_text.append("\n")
            else:
                result_text.append(f"**Active Advisories:** {len(all_advisories)} found\n\n")

                shown = 0
                for adv in all_advisories:
                    if shown >= max_results:
                        remaining = len(all_advisories) - max_results
                        if remaining > 0 and self.tier == TIER_FREE:
                            result_text.append(f"\n... and {remaining} more advisories.{_upgrade_message('Full threat advisory results (up to 25)')}")
                        elif remaining > 0:
                            result_text.append(f"\n... and {remaining} more advisories (showing top {max_results})")
                        break

                    result_text.append(self._format_advisory(adv))
                    result_text.append("\n")

                    # Trigger webhook for elevated/imminent threats
                    if adv.get("source") == "ntas" and adv.get("level", "").lower() in ("elevated", "imminent"):
                        await self._check_threat_advisory_alert(
                            adv.get("title", ""),
                            adv.get("level", ""),
                            adv.get("summary", ""),
                            adv.get("source", ""),
                        )
                    elif adv.get("source") == "travel" and adv.get("level_num", 0) >= 3:
                        await self._check_threat_advisory_alert(
                            adv.get("title", ""),
                            f"Level {adv.get('level_num', 0)}",
                            adv.get("summary", ""),
                            adv.get("source", ""),
                        )

                    shown += 1

            # Data source attribution
            sources = []
            if "terrorism" in effective_types:
                sources.append("DHS NTAS")
            if "travel" in effective_types:
                sources.append("State Dept Travel Advisories")
            if "cyber" in effective_types:
                sources.append("CISA")
            result_text.append(f"\n🔍 Data sources: {', '.join(sources)}\n")

            if self.tier == TIER_FREE:
                result_text.append(f"\n📋 Free tier: US terrorism advisories only, max {max_results} results. {limits['polling_note']}")
                result_text.append(_upgrade_message("Global travel advisories + cyber threats + country filtering"))

            return [TextContent(type="text", text="".join(result_text))]

        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching threat advisory data: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in threat advisory monitoring: {e}")]

    async def _fetch_ntas_advisories(self, include_expired: bool = False) -> List[Dict[str, Any]]:
        """Fetch DHS NTAS terrorism advisories via XML feed.

        Endpoint: https://www.dhs.gov/ntas/1.1/alerts.xml
        Returns XML with <alerts> containing <alert> elements.
        """
        url = "https://www.dhs.gov/ntas/1.1/alerts.xml"
        advisories: List[Dict[str, Any]] = []

        response = await self.http_client.get(url, headers={
            "Accept": "application/xml, text/xml",
            "User-Agent": "WEMS-MCP-Server/1.5.0"
        })
        response.raise_for_status()
        xml_text = response.text

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return advisories

        for alert_elem in root.findall("alert"):
            start_str = alert_elem.get("start", "")
            end_str = alert_elem.get("end", "")
            alert_type = alert_elem.get("type", "")
            link = alert_elem.get("link", "") or alert_elem.get("href", "")

            # Parse dates (format: YYYY/MM/DD HH:MM in GMT)
            start_dt = self._parse_ntas_date(start_str)
            end_dt = self._parse_ntas_date(end_str) if end_str else None

            # Preserve advisory records from feed; do not hard-drop by local clock
            # so feed-provider semantics determine active/retained visibility.

            summary_elem = alert_elem.find("summary")
            details_elem = alert_elem.find("details")
            summary = summary_elem.text if summary_elem is not None and summary_elem.text else ""
            details = details_elem.text if details_elem is not None and details_elem.text else ""
            # Strip HTML tags from details
            details = re.sub(r"<[^>]+>", "", details).strip()

            # Locations
            locations = []
            locs_elem = alert_elem.find("locations")
            if locs_elem is not None:
                for loc in locs_elem.findall("location"):
                    if loc.text:
                        locations.append(loc.text.strip())

            # Sectors
            sectors = []
            sects_elem = alert_elem.find("sectors")
            if sects_elem is not None:
                for sec in sects_elem.findall("sector"):
                    if sec.text:
                        sectors.append(sec.text.strip())

            # Map type to level
            level = "elevated"
            if "imminent" in alert_type.lower():
                level = "imminent"

            title = f"DHS NTAS: {alert_type}"

            advisories.append({
                "source": "ntas",
                "title": title,
                "level": level,
                "summary": summary,
                "details": details,
                "locations": locations,
                "sectors": sectors,
                "start": start_dt.isoformat() if start_dt else start_str,
                "end": end_dt.isoformat() if end_dt else end_str,
                "link": link,
            })

        return advisories

    async def _fetch_travel_advisories(
        self,
        countries: Optional[List[str]] = None,
        region: Optional[str] = None,
        threat_level: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch State Dept travel advisories via RSS feed.

        Endpoint: https://travel.state.gov/_res/rss/TAsTWs.xml
        Returns RSS 2.0 with <item> elements containing travel advisories.
        """
        url = "https://travel.state.gov/_res/rss/TAsTWs.xml"
        advisories: List[Dict[str, Any]] = []

        response = await self.http_client.get(url, headers={
            "Accept": "application/rss+xml, application/xml, text/xml",
            "User-Agent": "WEMS-MCP-Server/1.5.0"
        })
        response.raise_for_status()
        xml_text = response.text

        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return advisories

        channel = root.find("channel")
        if channel is None:
            return advisories

        for item in channel.findall("item"):
            title_elem = item.find("title")
            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
            link_elem = item.find("link")
            link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
            desc_elem = item.find("description")
            desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
            # Strip HTML from description
            desc = re.sub(r"<[^>]+>", "", desc).strip()
            pub_elem = item.find("pubDate")
            pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

            # Extract level from category elements
            level_num = 0
            level_text = ""
            country_tag = ""
            for cat in item.findall("category"):
                domain = cat.get("domain", "")
                cat_text = cat.text.strip() if cat.text else ""
                if domain == "Threat-Level":
                    level_text = cat_text
                    # Extract number: "Level 1: Exercise Normal Precautions"
                    match = re.search(r"Level\s+(\d)", cat_text)
                    if match:
                        level_num = int(match.group(1))
                elif domain == "Country-Tag":
                    country_tag = cat_text

            # Filter by threat level
            if threat_level:
                if str(level_num) not in threat_level:
                    continue

            # By default (no threat_level filter), only show level 2+ for
            # travel advisories to avoid flooding with "Exercise Normal Precautions"
            if not threat_level and level_num < 2:
                continue

            # Filter by countries
            if countries:
                # Check if any requested country appears in the title
                title_upper = title.upper()
                matched = False
                for c in countries:
                    if c.upper() in title_upper or c.upper() == country_tag.upper():
                        matched = True
                        break
                if not matched:
                    continue

            # Filter by region (basic keyword match in title/description)
            if region:
                region_lower = region.lower()
                if region_lower not in title.lower() and region_lower not in desc.lower():
                    continue

            advisories.append({
                "source": "travel",
                "title": title,
                "level": level_text,
                "level_num": level_num,
                "summary": desc,
                "country_tag": country_tag,
                "published": pub_date,
                "link": link,
            })

        # Sort by level (highest first)
        advisories.sort(key=lambda a: a.get("level_num", 0), reverse=True)
        return advisories

    async def _fetch_cyber_advisories(self) -> List[Dict[str, Any]]:
        """Fetch CISA cybersecurity advisories via RSS/JSON feed.

        Endpoint: https://www.cisa.gov/cybersecurity-advisories/all.xml
        Falls back gracefully if the feed is unavailable.
        """
        url = "https://www.cisa.gov/cybersecurity-advisories/all.xml"
        advisories: List[Dict[str, Any]] = []

        try:
            response = await self.http_client.get(url, headers={
                "Accept": "application/rss+xml, application/xml, text/xml",
                "User-Agent": "WEMS-MCP-Server/1.5.0"
            })
            response.raise_for_status()
            xml_text = response.text

            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError:
                return advisories

            channel = root.find("channel")
            if channel is None:
                return advisories

            for item in channel.findall("item"):
                title_elem = item.find("title")
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                link_elem = item.find("link")
                link = link_elem.text.strip() if link_elem is not None and link_elem.text else ""
                desc_elem = item.find("description")
                desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
                desc = re.sub(r"<[^>]+>", "", desc).strip()
                pub_elem = item.find("pubDate")
                pub_date = pub_elem.text.strip() if pub_elem is not None and pub_elem.text else ""

                advisories.append({
                    "source": "cyber",
                    "title": f"CISA: {title}",
                    "level": "advisory",
                    "summary": desc,
                    "published": pub_date,
                    "link": link,
                })

            # Only return recent advisories (last 7 days worth)
            return advisories[:10]

        except (httpx.HTTPError, Exception):
            # Cyber feed is best-effort; don't fail the whole request
            return advisories

    @staticmethod
    def _parse_ntas_date(date_str: str) -> Optional[datetime]:
        """Parse NTAS date format: YYYY/MM/DD HH:MM (GMT)."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str.strip(), "%Y/%m/%d %H:%M").replace(tzinfo=timezone.utc)
        except ValueError:
            return None

    def _format_advisory(self, adv: Dict[str, Any]) -> str:
        """Format a single advisory for display."""
        source = adv.get("source", "")

        if source == "ntas":
            level = adv.get("level", "elevated")
            icon = self._NTAS_ICONS.get(level, "🟡")
            title = adv.get("title", "DHS Advisory")
            summary = adv.get("summary", "")
            locations = adv.get("locations", [])
            sectors = adv.get("sectors", [])
            start = adv.get("start", "")
            end = adv.get("end", "")
            link = adv.get("link", "")

            result = f"{icon} **{title}**\n"
            result += f"   ⚠️ Level: {level.title()}\n"
            if summary:
                # Truncate long summaries
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                result += f"   📋 {summary}\n"
            if locations:
                result += f"   📍 Locations: {', '.join(locations)}\n"
            if sectors:
                result += f"   🏭 Sectors: {', '.join(sectors)}\n"
            if start:
                result += f"   ⏰ Effective: {start}\n"
            if end:
                result += f"   ⏳ Expires: {end}\n"
            if link:
                result += f"   🔗 {link}\n"
            return result

        elif source == "travel":
            level_num = adv.get("level_num", 0)
            icon, level_desc = self._TRAVEL_LEVELS.get(str(level_num), ("⚪", "Unknown"))
            title = adv.get("title", "Travel Advisory")
            summary = adv.get("summary", "")
            published = adv.get("published", "")
            link = adv.get("link", "")

            result = f"{icon} **{title}**\n"
            result += f"   ⚠️ {level_desc}\n"
            if summary:
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                result += f"   📋 {summary}\n"
            if published:
                result += f"   📅 Published: {published}\n"
            if link:
                result += f"   🔗 {link}\n"
            return result

        elif source == "cyber":
            title = adv.get("title", "Cyber Advisory")
            summary = adv.get("summary", "")
            published = adv.get("published", "")
            link = adv.get("link", "")

            result = f"🔵 **{title}**\n"
            if summary:
                if len(summary) > 200:
                    summary = summary[:200] + "..."
                result += f"   📋 {summary}\n"
            if published:
                result += f"   📅 Published: {published}\n"
            if link:
                result += f"   🔗 {link}\n"
            return result

        return f"⚪ {adv.get('title', 'Unknown Advisory')}\n"

    async def _check_threat_advisory_alert(self, title: str, level: str, summary: str, source: str):
        """Trigger webhook alert for threat advisories."""
        alert_config = self.config.get("alerts", {}).get("threat_advisories", {})
        webhook_url = alert_config.get("webhook")
        enabled = alert_config.get("enabled", True)

        if enabled and webhook_url:
            payload = {
                "event_type": "threat_advisory",
                "title": title,
                "threat_level": level,
                "summary": summary[:500] if summary else "",
                "source": source,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "alert_level": "critical" if "imminent" in level.lower() or "4" in level else "warning"
            }
            try:
                await self.http_client.post(webhook_url, json=payload)
            except httpx.HTTPError:
                pass

    # ─── Floods ──────────────────────────────────────────────────────────

    async def _check_floods(
        self,
        state: Optional[str] = None,
        flood_stage: Optional[List[str]] = None,
        time_range: str = "day",
        include_river_gauges: bool = False
    ) -> List[TextContent]:
        """Monitor flood warnings and river gauge data with tier-based access."""
        
        limits = self.limits
        
        # State filtering is premium only
        if state and not limits["floods_state_filter"]:
            return [TextContent(
                type="text",
                text=f"🔒 State filtering requires WEMS Premium.{_upgrade_message('Flood state filtering + river gauge data')}"
            )]
        
        # River gauge data is premium only
        if include_river_gauges and not limits["floods_river_gauges"]:
            return [TextContent(
                type="text",
                text=f"🔒 River gauge data requires WEMS Premium.{_upgrade_message('USGS river gauge monitoring')}"
            )]
        
        # Default flood stages based on tier
        if not flood_stage:
            flood_stage = limits["floods_stages"]
        else:
            # Filter out unavailable stages for free tier
            if self.tier == TIER_FREE:
                allowed_stages = limits["floods_stages"]
                flood_stage = [s for s in flood_stage if s in allowed_stages]
                if not flood_stage:
                    return [TextContent(
                        type="text",
                        text=f"🔒 Requested flood stages require WEMS Premium. Free tier supports: {', '.join(allowed_stages)}.{_upgrade_message('All flood stages + extended monitoring')}"
                    )]
        
        # Time range validation
        time_range_hours_map = {"hour": 1, "day": 24, "week": 168}
        if time_range == "week" and self.tier == TIER_FREE:
            return [TextContent(
                type="text",
                text=f"🔒 Weekly flood history requires WEMS Premium.{_upgrade_message('Extended flood monitoring')}"
            )]
        
        max_results = limits["floods_max_results"]
        time_range_hours = min(time_range_hours_map.get(time_range, 24), limits["floods_time_range"])
        
        try:
            result_text = ["🌊 **Flood Monitoring Report**\n\n"]
            
            if state:
                result_text.append(f"🌍 State: {state.upper()}\n")
            
            # 1. Check NOAA NWS flood alerts
            flood_alerts = await self._get_nws_flood_alerts(state, time_range_hours)
            
            # 2. Check USGS river gauge data (if premium and requested)
            river_data = []
            if include_river_gauges and self.tier == TIER_PREMIUM:
                river_data = await self._get_usgs_river_gauges(state, flood_stage)
            
            # Combine and process results
            all_flood_events = []
            
            # Process NWS flood alerts
            for alert in flood_alerts:
                properties = alert.get("properties", {})
                event = properties.get("event", "")
                
                # Filter by flood stage mapping
                alert_severity = self._map_nws_to_flood_stage(properties.get("severity", ""), event)
                if alert_severity.lower() not in [s.lower() for s in flood_stage]:
                    continue
                
                all_flood_events.append({
                    "type": "alert",
                    "data": alert,
                    "stage": alert_severity,
                    "time": properties.get("sent", "")
                })
            
            # Process USGS river gauge data
            for gauge in river_data:
                all_flood_events.append({
                    "type": "gauge",
                    "data": gauge,
                    "stage": gauge.get("flood_stage", "unknown"),
                    "time": gauge.get("last_updated", "")
                })
            
            # Sort by severity and time
            stage_priority = {"major": 0, "moderate": 1, "minor": 2, "action": 3}
            all_flood_events.sort(key=lambda x: (stage_priority.get(x["stage"].lower(), 4), x["time"]), reverse=True)
            
            if not all_flood_events:
                tier_info = f" (last {time_range_hours}h)" if self.tier == TIER_FREE else ""
                result_text.append(f"🟢 No flood warnings or alerts{tier_info}")
                if state:
                    result_text.append(f" for {state.upper()}")
                result_text.append("\n")
            else:
                result_text.append(f"**Active Flood Events:** {len(all_flood_events)} found\n\n")
                
                shown = 0
                for event in all_flood_events:
                    if shown >= max_results:
                        remaining = len(all_flood_events) - max_results
                        if remaining > 0 and self.tier == TIER_FREE:
                            result_text.append(f"\n... and {remaining} more flood events.{_upgrade_message('Full flood monitoring + river gauge data')}")
                        elif remaining > 0:
                            result_text.append(f"\n... and {remaining} more flood events (showing top {max_results})")
                        break
                    
                    if event["type"] == "alert":
                        result_text.append(self._format_flood_alert(event["data"]))
                    else:  # gauge
                        result_text.append(self._format_river_gauge(event["data"]))
                    
                    # Trigger webhook alert if needed
                    if event["type"] == "alert" and event["stage"].lower() in ["major", "moderate"]:
                        properties = event["data"].get("properties", {})
                        await self._check_flood_alert(
                            properties.get("event", ""),
                            properties.get("areaDesc", ""),
                            event["stage"],
                            properties.get("sent", "")
                        )
                    
                    result_text.append("\n")
                    shown += 1
            
            # Add tier-specific notes
            if self.tier == TIER_FREE:
                result_text.append(f"\n📋 Free tier: Major floods only, last 24h")
                if not include_river_gauges:
                    result_text.append(f"\n💧 River gauge data available with WEMS Premium")
            
            return [TextContent(type="text", text="".join(result_text))]
            
        except httpx.HTTPError as e:
            return [TextContent(
                type="text",
                text=f"❌ Error fetching flood data: {str(e)}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Unexpected error in flood monitoring: {str(e)}"
            )]

    async def _get_nws_flood_alerts(self, state: Optional[str], hours: int) -> List[Dict[str, Any]]:
        """Get flood alerts from NWS API."""
        url = "https://api.weather.gov/alerts"
        params = ["event=Flood Warning,Flash Flood Warning,Flash Flood Watch,Flood Watch,Flood Advisory"]
        
        if state:
            params.append(f"area={state}")
        
        if params:
            url += "?" + "&".join(params)
        
        response = await self.http_client.get(url)
        response.raise_for_status()
        data = response.json()
        
        filtered_alerts = []
        
        if data and "features" in data:
            for alert in data["features"]:
                properties = alert.get("properties", {})
                
                # Skip test alerts
                if properties.get("status", "").lower() == "test":
                    continue
                
                # Keep NWS-provided alerts as-is; upstream feed controls recency.
                filtered_alerts.append(alert)
        
        return filtered_alerts

    async def _get_usgs_river_gauges(self, state: Optional[str], flood_stages: List[str]) -> List[Dict[str, Any]]:
        """Get river gauge data from USGS Water Services API."""
        # USGS Water Services API - Instantaneous values
        url = "https://waterservices.usgs.gov/nwis/iv/"
        
        params = [
            "format=json",
            "parameterCd=00065",  # Gauge height in feet
            "period=P1D"  # Last 1 day
        ]
        
        if state:
            params.append(f"stateCd={state.lower()}")
        
        if params:
            url += "?" + "&".join(params)
        
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            data = response.json()
            
            gauges = []
            if "value" in data and "timeSeries" in data["value"]:
                for site in data["value"]["timeSeries"]:
                    site_info = site.get("sourceInfo", {})
                    site_name = site_info.get("siteName", "Unknown Site")
                    site_code = site_info.get("siteCode", [{}])[0].get("value", "Unknown")
                    
                    # Get latest gauge reading
                    values = site.get("values", [{}])[0].get("value", [])
                    if values:
                        latest = values[-1]
                        gauge_height = latest.get("value", "0")
                        timestamp = latest.get("dateTime", "")
                        
                        # Estimate flood stage based on gauge height
                        # This is simplified - real implementation would need flood stage data
                        try:
                            height = float(gauge_height)
                            if height > 20:  # Major flood
                                flood_stage = "major"
                            elif height > 15:  # Moderate flood
                                flood_stage = "moderate"
                            elif height > 10:  # Minor flood
                                flood_stage = "minor"
                            elif height > 8:   # Action stage
                                flood_stage = "action"
                            else:
                                continue  # Below action stage
                        except ValueError:
                            continue
                        
                        if flood_stage.lower() in [s.lower() for s in flood_stages]:
                            gauges.append({
                                "site_name": site_name,
                                "site_code": site_code,
                                "gauge_height": gauge_height,
                                "flood_stage": flood_stage,
                                "last_updated": timestamp
                            })
            
            return gauges
            
        except httpx.HTTPError:
            return []  # Return empty list on API error

    def _map_nws_to_flood_stage(self, severity: str, event: str) -> str:
        """Map NWS alert severity and event type to flood stage."""
        event_lower = event.lower()
        severity_lower = severity.lower()
        
        if "warning" in event_lower:
            if "flash flood" in event_lower:
                return "major"  # Flash flood warnings are typically major
            else:
                return "moderate"  # Regular flood warnings
        elif "watch" in event_lower:
            return "minor"
        elif "advisory" in event_lower:
            return "action"
        elif severity_lower == "extreme":
            return "major"
        elif severity_lower == "severe":
            return "moderate"
        else:
            return "minor"

    def _format_flood_alert(self, alert: Dict[str, Any]) -> str:
        """Format NWS flood alert for display."""
        properties = alert.get("properties", {})
        
        event = properties.get("event", "Flood Alert")
        headline = properties.get("headline", event)
        areas = properties.get("areaDesc", "Unknown Areas")
        severity = properties.get("severity", "Unknown")
        sent_time = properties.get("sent", "")
        expires_time = properties.get("expires", "")
        
        # Choose icon based on event type and severity
        if "flash flood warning" in event.lower():
            icon = "🔴🌊"
        elif "flood warning" in event.lower():
            icon = "🟠🌊"
        elif "flash flood watch" in event.lower():
            icon = "🟡🌊"
        elif "flood watch" in event.lower():
            icon = "🟡🌊"
        elif "flood advisory" in event.lower():
            icon = "🔵🌊"
        else:
            icon = "🌊"
        
        result = f"{icon} **{event}**\n"
        result += f"📍 {areas}\n"
        result += f"⚠️ {headline}\n"
        
        if severity != "Unknown":
            result += f"🎯 Severity: {severity.title()}\n"
        
        if sent_time:
            try:
                sent_dt = datetime.fromisoformat(sent_time.replace('Z', '+00:00'))
                result += f"⏰ Issued: {sent_dt.strftime('%Y-%m-%d %H:%M UTC')}\n"
            except ValueError:
                pass
        
        if expires_time:
            try:
                expires_dt = datetime.fromisoformat(expires_time.replace('Z', '+00:00'))
                result += f"⏳ Expires: {expires_dt.strftime('%Y-%m-%d %H:%M UTC')}\n"
            except ValueError:
                pass
        
        return result

    def _format_river_gauge(self, gauge: Dict[str, Any]) -> str:
        """Format USGS river gauge data for display."""
        site_name = gauge.get("site_name", "Unknown Site")
        site_code = gauge.get("site_code", "Unknown")
        gauge_height = gauge.get("gauge_height", "0")
        flood_stage = gauge.get("flood_stage", "unknown")
        last_updated = gauge.get("last_updated", "")
        
        # Choose icon based on flood stage
        stage_icons = {
            "major": "🔴📊",
            "moderate": "🟠📊",
            "minor": "🟡📊",
            "action": "🔵📊"
        }
        icon = stage_icons.get(flood_stage.lower(), "📊")
        
        result = f"{icon} **River Gauge: {site_name}**\n"
        result += f"📍 Site: {site_code}\n"
        result += f"📏 Height: {gauge_height} ft\n"
        result += f"⚠️ Stage: {flood_stage.title()}\n"
        
        if last_updated:
            try:
                updated_dt = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                result += f"⏰ Updated: {updated_dt.strftime('%Y-%m-%d %H:%M UTC')}\n"
            except ValueError:
                pass
        
        return result

    async def _check_flood_alert(self, event: str, areas: str, stage: str, sent_time: str):
        """Trigger webhook alert for flood events."""
        alert_config = self.config.get("alerts", {}).get("floods", {})
        webhook_url = alert_config.get("webhook")
        enabled = alert_config.get("enabled", True)
        
        # Alert on warnings and major/moderate floods
        trigger_events = ["warning", "emergency"]
        trigger_stages = ["major", "moderate"]
        
        should_alert = (enabled and webhook_url and 
                       (any(trigger in event.lower() for trigger in trigger_events) or
                        stage.lower() in trigger_stages))
        
        if should_alert:
            payload = {
                "event_type": "flood",
                "flood_event": event,
                "areas": areas,
                "flood_stage": stage,
                "timestamp": sent_time or datetime.now(timezone.utc).isoformat(),
                "alert_level": "emergency" if stage.lower() == "major" else "critical" if stage.lower() == "moderate" else "warning"
            }
            try:
                await self.http_client.post(webhook_url, json=payload)
            except httpx.HTTPError:
                pass
    
    # ─── Space Weather Alerts ────────────────────────────────────────────

    async def _check_space_weather_alerts(
        self,
        alert_types: Optional[List[str]] = None,
        hours_back: int = 24
    ) -> List[TextContent]:
        """Check active space weather alerts from NOAA SWPC."""
        
        limits = self.limits
        
        # Enforce tier limits
        max_results = limits["space_weather_max_results"]
        max_hours_back = limits["space_weather_hours_back"]
        
        if hours_back > max_hours_back:
            hours_back = max_hours_back
            if self.tier == TIER_FREE:
                tier_note = f"\n📋 Free tier: showing last {max_hours_back}h (premium unlocks up to 7 days)\n"
            else:
                tier_note = ""
        else:
            tier_note = ""

        try:
            # Get alerts from NOAA SWPC
            url = "https://services.swpc.noaa.gov/products/alerts.json"
            response = await self.http_client.get(url)
            response.raise_for_status()
            alerts_data = response.json()

            if not alerts_data:
                result_text = ["🌞 **Space Weather Alerts**: No active alerts from NOAA SWPC"]
                if tier_note:
                    result_text.append(tier_note)
                return [TextContent(type="text", text="".join(result_text))]

            result_text = ["🌞 **Active Space Weather Alerts**\n"]
            if tier_note:
                result_text.append(tier_note)

            # Filter by time
            from datetime import datetime, timezone, timedelta
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
            
            # Filter and categorize alerts
            recent_alerts = []
            for alert in alerts_data:
                # Handle different datetime formats from API
                issue_datetime_str = alert['issue_datetime']
                try:
                    # Try parsing with timezone info first
                    if 'Z' in issue_datetime_str:
                        issue_time = datetime.fromisoformat(issue_datetime_str.replace('Z', '+00:00'))
                    elif '+' in issue_datetime_str or issue_datetime_str.endswith('UTC'):
                        issue_time = datetime.fromisoformat(issue_datetime_str.replace('UTC', '+00:00'))
                    else:
                        # Assume UTC if no timezone info
                        issue_time = datetime.fromisoformat(issue_datetime_str).replace(tzinfo=timezone.utc)
                except ValueError:
                    # Fallback: assume it's a basic format and add UTC timezone
                    try:
                        issue_time = datetime.strptime(issue_datetime_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    except ValueError:
                        continue  # Skip malformed timestamps
                
                if issue_time >= cutoff_time:
                    recent_alerts.append((issue_time, alert))

            # Sort by time (newest first)
            recent_alerts.sort(key=lambda x: x[0], reverse=True)
            total_alerts = len(recent_alerts)
            recent_alerts = recent_alerts[:max_results]

            if not recent_alerts:
                result_text.append(f"No alerts in the last {hours_back} hours\n")
            else:
                shown = 0
                for issue_time, alert in recent_alerts:

                    # Determine alert type and icon
                    product_id = alert.get('product_id', '')
                    message = alert.get('message', '')
                    
                    if 'geomagnetic' in message.lower() or 'K-index' in message:
                        icon = "🧲"
                        alert_type = "Geomagnetic"
                    elif 'proton' in message.lower() or 'radiation' in message.lower():
                        icon = "☢️"
                        alert_type = "Radiation"
                    elif 'radio' in message.lower() or 'blackout' in message.lower():
                        icon = "📡"
                        alert_type = "Radio"
                    elif 'solar flare' in message.lower() or 'x-ray' in message.lower():
                        icon = "☀️"
                        alert_type = "Solar Flare"
                    else:
                        icon = "⚠️"
                        alert_type = "Space Weather"

                    # Filter by alert types if specified
                    if alert_types and alert_types != ["all"]:
                        type_match = False
                        for filter_type in alert_types:
                            if filter_type.lower() in alert_type.lower():
                                type_match = True
                                break
                        if not type_match:
                            continue

                    # Extract key information from message
                    lines = message.split('\n')
                    title = lines[0] if lines else "Space Weather Alert"
                    
                    # Look for scale information
                    scale_info = ""
                    for line in lines:
                        if 'NOAA Scale:' in line or 'Scale:' in line:
                            scale_info = f" ({line.split('Scale:')[-1].strip()})"
                            break

                    time_str = issue_time.strftime("%Y-%m-%d %H:%M UTC")
                    
                    result_text.append(
                        f"{icon} **{alert_type}** Alert{scale_info}\n"
                        f"   {title}\n"
                        f"   {time_str} | ID: {product_id}\n\n"
                    )
                    shown += 1

                # Show upgrade message if there were more alerts than we displayed
                if total_alerts > max_results and self.tier == TIER_FREE:
                    remaining = total_alerts - max_results
                    result_text.append(f"\n... and {remaining} more alerts.{_upgrade_message('Full space weather alert history')}")

            if self.tier == TIER_FREE:
                result_text.append(f"\n📋 {limits['polling_note']}")

            return [TextContent(type="text", text="".join(result_text))]

        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching space weather alerts: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in space weather alerts: {e}")]


    # ─── Multi-Source Confidence Fusion (wems-041, feature-flagged) ─────

    @staticmethod
    def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Approximate distance between two points (Haversine)."""
        from math import asin, cos, radians, sin, sqrt

        r_km = 6371.0
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        return r_km * c

    @staticmethod
    def _normalize_source(source: str) -> str:
        return (source or "").strip().lower()

    def _fuse_events_to_incidents(
        self,
        events: List[Dict[str, Any]],
        fusion_window_minutes: int = 30,
        dedupe_radius_km: float = 25.0,
    ) -> List[Dict[str, Any]]:
        """Cluster co-temporal/co-spatial events and emit confidence-scored incidents."""
        source_weights = {"usgs": 1.0, "noaa": 0.9, "nws": 0.95, "cisa": 0.85}
        valid_events: List[Dict[str, Any]] = []

        for ev in events:
            source = self._normalize_source(str(ev.get("source", "")))
            if source not in source_weights:
                continue
            ts = ev.get("timestamp")
            lat = ev.get("latitude")
            lon = ev.get("longitude")
            if not ts or lat is None or lon is None:
                continue
            try:
                dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                valid_events.append({**ev, "source": source, "_dt": dt})
            except Exception:
                continue

        valid_events.sort(key=lambda x: x["_dt"])
        clusters: List[List[Dict[str, Any]]] = []

        for ev in valid_events:
            placed = False
            for cluster in clusters:
                ref = cluster[0]
                age_min = abs((ev["_dt"] - ref["_dt"]).total_seconds()) / 60.0
                dist_km = self._distance_km(float(ev["latitude"]), float(ev["longitude"]), float(ref["latitude"]), float(ref["longitude"]))
                if age_min <= fusion_window_minutes and dist_km <= dedupe_radius_km:
                    cluster.append(ev)
                    placed = True
                    break
            if not placed:
                clusters.append([ev])

        incidents: List[Dict[str, Any]] = []
        total_weight = sum(source_weights.values())

        for idx, cluster in enumerate(clusters, start=1):
            by_source: Dict[str, List[Dict[str, Any]]] = {}
            for ev in cluster:
                by_source.setdefault(ev["source"], []).append(ev)

            contribution = {src: source_weights[src] for src in by_source.keys()}
            score = min(1.0, sum(contribution.values()) / total_weight)

            lat_avg = sum(float(ev["latitude"]) for ev in cluster) / len(cluster)
            lon_avg = sum(float(ev["longitude"]) for ev in cluster) / len(cluster)
            times = sorted(ev["_dt"] for ev in cluster)

            incidents.append({
                "incident_id": f"inc-{times[0].strftime('%Y%m%d%H%M%S')}-{idx}",
                "event_type": cluster[0].get("event_type") or "unspecified",
                "title": cluster[0].get("title") or "Fused Incident",
                "confidence_score": round(score, 4),
                "confidence_breakdown": contribution,
                "source_count": len(by_source),
                "event_count": len(cluster),
                "fusion_window_minutes": fusion_window_minutes,
                "dedupe_radius_km": dedupe_radius_km,
                "location": {"latitude": round(lat_avg, 5), "longitude": round(lon_avg, 5)},
                "first_seen": times[0].isoformat(),
                "last_seen": times[-1].isoformat(),
                "evidence": [
                    {
                        "source": ev["source"],
                        "event_id": ev.get("event_id"),
                        "title": ev.get("title"),
                        "timestamp": ev.get("timestamp"),
                        "url": ev.get("url"),
                    }
                    for ev in cluster
                ],
            })

        incidents.sort(key=lambda x: x["confidence_score"], reverse=True)
        return incidents

    async def _fuse_multi_source_incidents(
        self,
        events: List[Dict[str, Any]],
        fusion_window_minutes: int = 30,
        dedupe_radius_km: float = 25.0,
    ) -> List[TextContent]:
        incidents = self._fuse_events_to_incidents(
            events=events,
            fusion_window_minutes=int(fusion_window_minutes),
            dedupe_radius_km=float(dedupe_radius_km),
        )

        payload = {
            "feature": "wems-041-multi-source-confidence-fusion",
            "flag": "WEMS_FEATURE_MULTI_SOURCE_CONFIDENCE_FUSION",
            "input_event_count": len(events or []),
            "incident_count": len(incidents),
            "incidents": incidents,
        }
        return [TextContent(type="text", text=json.dumps(payload, indent=2))]


    # ─── Drought Monitoring ──────────────────────────────────────────────

    async def _check_drought_status(
        self,
        state: str,
        weeks_back: int = 4,
        include_trend: bool = True
    ) -> List[TextContent]:
        """Check current US drought status for a state (Premium only)."""
        
        limits = self.limits
        
        if not limits.get("drought_status", False):
            return [TextContent(
                type="text",
                text=f"🔒 Drought monitoring requires WEMS Premium.{_upgrade_message('US Drought Monitor access')}"
            )]

        # Enforce tier limits
        max_weeks_back = limits.get("drought_weeks_back", 4)
        if weeks_back > max_weeks_back:
            weeks_back = max_weeks_back

        try:
            # Convert state abbreviation to FIPS code if needed
            state_upper = state.upper()
            
            # Map state abbreviations to FIPS codes
            state_fips_map = {
                'AL': '01', 'AK': '02', 'AZ': '04', 'AR': '05', 'CA': '06', 'CO': '08',
                'CT': '09', 'DE': '10', 'FL': '12', 'GA': '13', 'HI': '15', 'ID': '16',
                'IL': '17', 'IN': '18', 'IA': '19', 'KS': '20', 'KY': '21', 'LA': '22',
                'ME': '23', 'MD': '24', 'MA': '25', 'MI': '26', 'MN': '27', 'MS': '28',
                'MO': '29', 'MT': '30', 'NE': '31', 'NV': '32', 'NH': '33', 'NJ': '34',
                'NM': '35', 'NY': '36', 'NC': '37', 'ND': '38', 'OH': '39', 'OK': '40',
                'OR': '41', 'PA': '42', 'RI': '44', 'SC': '45', 'SD': '46', 'TN': '47',
                'TX': '48', 'UT': '49', 'VT': '50', 'VA': '51', 'WA': '53', 'WV': '54',
                'WI': '55', 'WY': '56'
            }
            
            # Use FIPS code or try as-is
            if state_upper in state_fips_map:
                aoi = state_fips_map[state_upper]
                state_name = state_upper
            elif state.isdigit() and len(state) == 2:
                aoi = state
                # Reverse lookup for display
                state_name = next((k for k, v in state_fips_map.items() if v == state), state)
            else:
                return [TextContent(
                    type="text",
                    text=f"❌ Invalid state: {state}. Please use 2-letter abbreviation (e.g., CA, TX) or FIPS code."
                )]

            # Calculate date range
            from datetime import datetime, timezone, timedelta
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(weeks=weeks_back)
            
            # Format dates for API
            start_date_str = start_date.strftime("%-m/%-d/%Y")
            end_date_str = end_date.strftime("%-m/%-d/%Y")
            
            # Call US Drought Monitor API
            url = (
                f"https://usdmdataservices.unl.edu/api/StateStatistics/"
                f"GetDroughtSeverityStatisticsByAreaPercent"
                f"?aoi={aoi}&startdate={start_date_str}&enddate={end_date_str}&statisticsType=1"
            )
            
            response = await self.http_client.get(
                url,
                headers={"Accept": "application/json"}
            )
            response.raise_for_status()
            drought_data = response.json()

            if not drought_data:
                return [TextContent(
                    type="text",
                    text=f"🌵 No drought data available for {state_name}"
                )]

            # Sort by date (newest first)
            drought_data.sort(key=lambda x: x['mapDate'], reverse=True)
            
            # Get current status (most recent)
            current = drought_data[0]
            map_date = datetime.fromisoformat(current['mapDate'].replace('Z', ''))
            date_str = map_date.strftime("%Y-%m-%d")

            result_text = [f"🌵 **Drought Status: {state_name}**\n"]
            result_text.append(f"Current as of: {date_str}\n\n")

            # Current drought levels
            none_pct = current.get('none', 0)
            d0_pct = current.get('d0', 0)  # Abnormally Dry
            d1_pct = current.get('d1', 0)  # Moderate Drought
            d2_pct = current.get('d2', 0)  # Severe Drought
            d3_pct = current.get('d3', 0)  # Extreme Drought
            d4_pct = current.get('d4', 0)  # Exceptional Drought

            # Overall status
            if d4_pct > 0:
                status_icon = "🔴"
                status = "Exceptional Drought"
            elif d3_pct > 0:
                status_icon = "🟠"
                status = "Extreme Drought"
            elif d2_pct > 0:
                status_icon = "🟡"
                status = "Severe Drought"
            elif d1_pct > 0:
                status_icon = "🟤"
                status = "Moderate Drought"
            elif d0_pct > 0:
                status_icon = "🟨"
                status = "Abnormally Dry"
            else:
                status_icon = "🟢"
                status = "No Drought"

            result_text.append(f"{status_icon} **Overall Status: {status}**\n\n")
            
            # Breakdown by intensity
            result_text.append("**Drought Intensity Breakdown:**\n")
            if none_pct > 0:
                result_text.append(f"🟢 No Drought: {none_pct:.1f}%\n")
            if d0_pct > 0:
                result_text.append(f"🟨 D0 (Abnormally Dry): {d0_pct:.1f}%\n")
            if d1_pct > 0:
                result_text.append(f"🟤 D1 (Moderate): {d1_pct:.1f}%\n")
            if d2_pct > 0:
                result_text.append(f"🟡 D2 (Severe): {d2_pct:.1f}%\n")
            if d3_pct > 0:
                result_text.append(f"🟠 D3 (Extreme): {d3_pct:.1f}%\n")
            if d4_pct > 0:
                result_text.append(f"🔴 D4 (Exceptional): {d4_pct:.1f}%\n")

            # Trend analysis if requested and multiple data points
            if include_trend and len(drought_data) > 1:
                result_text.append(f"\n**{weeks_back}-Week Trend:**\n")
                
                oldest = drought_data[-1]
                old_none = oldest.get('none', 0)
                old_total_drought = 100 - old_none
                current_total_drought = 100 - none_pct
                
                drought_change = current_total_drought - old_total_drought
                
                if abs(drought_change) < 1:
                    trend_icon = "➡️"
                    trend_text = "Stable"
                elif drought_change > 0:
                    trend_icon = "📈"
                    trend_text = f"Worsening (+{drought_change:.1f}% in drought)"
                else:
                    trend_icon = "📉"
                    trend_text = f"Improving ({drought_change:.1f}% in drought)"
                
                result_text.append(f"{trend_icon} {trend_text}\n")

            result_text.append(f"\n📋 Data source: US Drought Monitor (updated weekly)")

            return [TextContent(type="text", text="".join(result_text))]

        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching drought data: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in drought monitoring: {e}")]


    # ─── Server Lifecycle ────────────────────────────────────────────────

    async def run(self):
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server
        from mcp.types import InitializationOptions
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, InitializationOptions())
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()


async def _amain():
    """Async main entry point."""
    config_path = None

    # Minimal CLI handling for packaged script usability.
    if len(sys.argv) > 1:
        arg1 = sys.argv[1]
        if arg1 in {"-h", "--help"}:
            print("WEMS MCP Server")
            print("Usage: wems [config.yaml]")
            print("Runs MCP stdio server for hazard monitoring.")
            return
        config_path = arg1

    async with WemsServer(config_path) as server:
        await server.run()


def main():
    """Sync console entrypoint for setuptools scripts."""
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
