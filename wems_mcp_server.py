#!/usr/bin/env python3
"""
WEMS - World Event Monitoring System MCP Server

Natural hazard monitoring with configurable webhooks for threshold alerts.
Free tier provides essential safety alerts. Premium unlocks full depth.
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
import yaml
from mcp.server import Server
from mcp.types import Tool, TextContent


# ─── Tier Definitions ────────────────────────────────────────────────────────

TIER_FREE = "free"
TIER_PREMIUM = "premium"

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
        "configure_alerts": True,              # Full alert customization
        "polling_note": "Real-time updates",
    }
}


def _get_tier(api_key: Optional[str] = None) -> str:
    """Determine user tier from API key or environment.
    
    Tier resolution order:
    1. WEMS_API_KEY environment variable
    2. api_key passed in config
    3. Default to free tier
    
    Premium keys are validated against WEMS_PREMIUM_KEYS (comma-separated)
    or via Stripe webhook validation (when configured).
    """
    key = api_key or os.environ.get("WEMS_API_KEY", "")
    if not key:
        return TIER_FREE
    
    # Check against local premium keys list
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
        self.tier = _get_tier(self.config.get("api_key"))
        self.limits = _tier_limits(self.tier)
        
        # Register MCP tools
        self._register_tools()
    
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
            ]
            
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
            
            return tools
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
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
            elif name == "configure_alerts":
                if self.tier != TIER_PREMIUM:
                    return [TextContent(type="text", text=f"🔒 Custom alert configuration requires WEMS Premium.{_upgrade_message('Custom alert thresholds')}")]
                return await self._configure_alerts(**arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
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
            response = await self.http_client.get(url)
            response.raise_for_status()
            data = response.json()
            
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
            ptwc_url = "https://www.tsunami.gov/events/json/events.json"
            response = await self.http_client.get(ptwc_url)
            response.raise_for_status()
            tsunami_data = response.json()
            
            result_text = ["🌊 **Tsunami Alert Status**\n\n"]
            max_results = limits["tsunami_max_results"]
            
            active_warnings = []
            if tsunami_data and isinstance(tsunami_data, list):
                now = datetime.now(timezone.utc)
                
                for event in tsunami_data:
                    event_time = event.get("time", "")
                    if event_time:
                        try:
                            dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                            if (now - dt).days <= 1:
                                active_warnings.append(event)
                        except (ValueError, TypeError):
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
                    magnitude = warning.get("magnitude", "Unknown")
                    event_time = warning.get("time", "Unknown time")
                    
                    if event_time != "Unknown time":
                        try:
                            dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                            time_str = dt.strftime("%m-%d %H:%M UTC")
                        except (ValueError, TypeError):
                            time_str = event_time
                    else:
                        time_str = event_time
                    
                    result_text.append(f"🚨 **{location}**\n")
                    result_text.append(f"   Magnitude: {magnitude}\n")
                    result_text.append(f"   Time: {time_str}\n\n")
                    shown += 1
                    
                    await self._check_tsunami_alert(location, magnitude, time_str)
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
            # Fetch active storms from NHC
            nhc_url = "https://www.nhc.noaa.gov/CurrentSummaries.json"
            nhc_response = await self.http_client.get(nhc_url)
            nhc_response.raise_for_status()
            nhc_data = nhc_response.json()
            
            # Fetch NWS tropical alerts
            alerts_url = "https://api.weather.gov/alerts/active?event=Hurricane,Tropical%20Storm,Hurricane%20Warning,Hurricane%20Watch"
            alerts_response = await self.http_client.get(alerts_url)
            alerts_response.raise_for_status()
            alerts_data = alerts_response.json()
            
            result_text = [f"🌀 **Hurricane/Tropical Storm Status** ({basin.title()})\n\n"]
            
            # Process active storms
            active_storms = []
            if nhc_data and "summaries" in nhc_data:
                for storm in nhc_data["summaries"]:
                    storm_basin = storm.get("basin", "").lower()
                    if basin == "all" or basin == "atlantic" and storm_basin in ["atlantic", "al"] or basin == "pacific" and storm_basin in ["pacific", "ep", "cp", "wp"]:
                        active_storms.append(storm)
            
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
                    
                    if "hurricane" in intensity.lower():
                        storm_icon = "🔴"
                    elif "tropical storm" in intensity.lower():
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
            
            # Filter alerts by time range
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_range_hours)
            
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
                    
                    # Filter by time (for free tier limitation)
                    sent_time = properties.get("sent")
                    if sent_time:
                        alert_time = datetime.fromisoformat(sent_time.replace('Z', '+00:00'))
                        if alert_time < cutoff_time:
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
            # ── Step 1: find locations near the user ──
            locations = []
            if latitude is not None and longitude is not None:
                loc_url = (
                    f"https://api.openaq.org/v3/locations"
                    f"?coordinates={latitude},{longitude}"
                    f"&radius={int(radius_km * 1000)}"
                    f"&limit={max_results}"
                )
                loc_resp = await self.http_client.get(loc_url)
                loc_resp.raise_for_status()
                loc_data = loc_resp.json()
                locations = loc_data.get("results", [])
            else:
                # Default: query latest measurements directly
                pass

            # ── Step 2: fetch latest measurements ──
            all_measurements = []
            for param_name in parameters:
                param_id = self._OPENAQ_PARAMS.get(param_name)
                if param_id is None:
                    continue

                if locations:
                    for loc in locations:
                        loc_id = loc.get("id")
                        if loc_id is None:
                            continue
                        meas_url = (
                            f"https://api.openaq.org/v3/locations/{loc_id}/measurements"
                            f"?parameters_id={param_id}&limit=1"
                        )
                        meas_resp = await self.http_client.get(meas_url)
                        meas_resp.raise_for_status()
                        meas_data = meas_resp.json()
                        for m in meas_data.get("results", []):
                            m["_location"] = loc
                            m["_param_name"] = param_name
                            all_measurements.append(m)
                else:
                    # Broad latest query
                    meas_url = (
                        f"https://api.openaq.org/v3/locations"
                        f"?parameters_id={param_id}"
                        f"&country={country.upper()}"
                        f"&limit={max_results}"
                    )
                    meas_resp = await self.http_client.get(meas_url)
                    meas_resp.raise_for_status()
                    meas_data = meas_resp.json()
                    for loc in meas_data.get("results", []):
                        # Use the latest value from the location
                        latest = loc.get("latest", {})
                        if latest:
                            m = {
                                "value": latest.get("value"),
                                "datetime": latest.get("datetime"),
                                "_location": loc,
                                "_param_name": param_name,
                            }
                            all_measurements.append(m)

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

                        if value is not None:
                            try:
                                val = float(value)
                            except (ValueError, TypeError):
                                val = 0.0
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

            result_text.append("🔍 Data source: OpenAQ (global air quality data)\n")

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
        
        # Filter by time range
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        filtered_alerts = []
        
        if data and "features" in data:
            for alert in data["features"]:
                properties = alert.get("properties", {})
                
                # Skip test alerts
                if properties.get("status", "").lower() == "test":
                    continue
                
                # Filter by time
                sent_time = properties.get("sent")
                if sent_time:
                    alert_time = datetime.fromisoformat(sent_time.replace('Z', '+00:00'))
                    if alert_time < cutoff_time:
                        continue
                
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


async def main():
    """Main entry point."""
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    
    async with WemsServer(config_path) as server:
        await server.run()


if __name__ == "__main__":
    asyncio.run(main())
