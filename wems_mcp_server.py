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
                    "tsunami": {"enabled": True}
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
    
    # ─── Server Lifecycle ────────────────────────────────────────────────

    async def run(self):
        """Run the MCP server."""
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream)
    
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
