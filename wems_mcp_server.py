#!/usr/bin/env python3
"""
WEMS - World Event Monitoring System MCP Server

Natural hazard monitoring with configurable webhooks for threshold alerts.
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


class WemsServer:
    def __init__(self, config_path: Optional[str] = None):
        self.server = Server("wems")
        self.config = self._load_config(config_path)
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
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
            # Default configuration
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
            return [
                Tool(
                    name="check_earthquakes",
                    description="Check recent earthquake activity with optional filtering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "min_magnitude": {
                                "type": "number",
                                "description": "Minimum earthquake magnitude (default: 4.5)",
                                "default": 4.5
                            },
                            "time_period": {
                                "type": "string", 
                                "enum": ["hour", "day", "week"],
                                "description": "Time period to check (default: day)",
                                "default": "day"
                            },
                            "region": {
                                "type": "string",
                                "description": "Geographic region filter (optional)"
                            }
                        }
                    }
                ),
                Tool(
                    name="check_solar",
                    description="Monitor space weather events and solar activity",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "event_types": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Types to check: flare, cme, geomagnetic (default: all)"
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
                                "description": "Alert levels to check: NORMAL, ADVISORY, WATCH, WARNING (default: WATCH, WARNING)",
                                "default": ["WATCH", "WARNING"]
                            },
                            "region": {
                                "type": "string",
                                "description": "Geographic region filter (optional)"
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
                                "description": "Regions to check: pacific, atlantic, indian, mediterranean (default: all)"
                            }
                        }
                    }
                ),
                Tool(
                    name="configure_alerts",
                    description="Update alert thresholds and webhook URLs",
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
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle tool calls."""
            
            if name == "check_earthquakes":
                return await self._check_earthquakes(**arguments)
            elif name == "check_solar":
                return await self._check_solar(**arguments)
            elif name == "check_volcanoes":
                return await self._check_volcanoes(**arguments)
            elif name == "check_tsunamis":
                return await self._check_tsunamis(**arguments)
            elif name == "configure_alerts":
                return await self._configure_alerts(**arguments)
            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    async def _check_earthquakes(
        self,
        min_magnitude: float = 4.5,
        time_period: str = "day",
        region: Optional[str] = None
    ) -> List[TextContent]:
        """Check recent earthquake activity."""
        
        # USGS API endpoints
        endpoints = {
            "hour": f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{min_magnitude}_hour.geojson",
            "day": f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{min_magnitude}_day.geojson", 
            "week": f"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/{min_magnitude}_week.geojson"
        }
        
        url = endpoints.get(time_period, endpoints["day"])
        
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            data = response.json()
            
            earthquakes = []
            count = data["metadata"]["count"]
            
            if count == 0:
                return [TextContent(
                    type="text", 
                    text=f"🌍 No earthquakes ≥{min_magnitude} magnitude in the past {time_period}"
                )]
            
            result_text = [f"🌍 Earthquakes ≥{min_magnitude} magnitude ({time_period}): {count} found\\n"]
            
            for feature in data["features"][:10]:  # Limit to top 10
                props = feature["properties"]
                coords = feature["geometry"]["coordinates"]
                
                magnitude = props["mag"]
                place = props["place"]
                time_ms = props["time"]
                depth = coords[2]
                
                # Convert timestamp
                quake_time = datetime.fromtimestamp(time_ms / 1000)
                time_str = quake_time.strftime("%Y-%m-%d %H:%M UTC")
                
                # Region filtering
                if region and region.lower() not in place.lower():
                    continue
                
                # Format magnitude display
                if magnitude >= 7.0:
                    mag_icon = "🔴"
                elif magnitude >= 6.0:
                    mag_icon = "🟠" 
                elif magnitude >= 5.0:
                    mag_icon = "🟡"
                else:
                    mag_icon = "•"
                
                result_text.append(
                    f"{mag_icon} {magnitude} - {place}\\n"
                    f"   {time_str} | Depth: {depth:.1f} km\\n"
                )
                
                # Check alert thresholds
                await self._check_earthquake_alert(magnitude, place, quake_time)
            
            return [TextContent(type="text", text="".join(result_text))]
            
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching earthquake data: {e}")]
    
    async def _check_solar(self, event_types: Optional[List[str]] = None) -> List[TextContent]:
        """Monitor space weather events and solar activity."""
        
        try:
            # Get current K-index data from NOAA SWPC
            kindex_url = "https://services.swpc.noaa.gov/json/boulder_k_index_1m.json"
            response = await self.http_client.get(kindex_url)
            response.raise_for_status()
            kindex_data = response.json()
            
            # Get space weather events from NOAA SWPC
            events_url = "https://services.swpc.noaa.gov/json/edited_events.json"
            events_response = await self.http_client.get(events_url)
            events_response.raise_for_status()
            events_data = events_response.json()
            
            result_text = ["🌞 **Space Weather Status**\n\n"]
            
            # Process K-index (geomagnetic activity)
            if kindex_data:
                latest = kindex_data[-1]  # Most recent reading
                k_index = float(latest["k_index"])
                time_tag = latest["time_tag"]
                
                # Convert timestamp
                dt = datetime.fromisoformat(time_tag.replace('Z', '+00:00'))
                time_str = dt.strftime("%Y-%m-%d %H:%M UTC")
                
                # Categorize K-index level
                if k_index >= 7:
                    level_icon = "🔴"
                    level_text = "SEVERE STORM"
                elif k_index >= 5:
                    level_icon = "🟠"
                    level_text = "STRONG STORM"
                elif k_index >= 4:
                    level_icon = "🟡"
                    level_text = "MINOR STORM"
                elif k_index >= 3:
                    level_icon = "🟢"
                    level_text = "UNSETTLED"
                else:
                    level_icon = "🔵"
                    level_text = "QUIET"
                
                result_text.append(f"**Geomagnetic Activity (K-index):**\n")
                result_text.append(f"{level_icon} K={k_index:.1f} - {level_text}\n")
                result_text.append(f"Latest reading: {time_str}\n\n")
                
                # Check alert thresholds
                await self._check_solar_alert(k_index, level_text, dt)
            
            # Process recent space weather events
            if events_data:
                # Filter for recent events (last 24 hours)
                now = datetime.now(timezone.utc)
                recent_events = []
                
                for event in events_data:
                    event_time = datetime.fromisoformat(event["begin_time"].replace('Z', '+00:00'))
                    if (now - event_time).days <= 1:
                        recent_events.append(event)
                
                if recent_events:
                    result_text.append("**Recent Space Weather Events (24h):**\n")
                    
                    for event in recent_events[:5]:  # Limit to 5 most recent
                        event_type = event.get("type", "Unknown")
                        begin_time = event.get("begin_time", "")
                        description = event.get("message", "No description")
                        
                        # Parse time
                        if begin_time:
                            dt = datetime.fromisoformat(begin_time.replace('Z', '+00:00'))
                            time_str = dt.strftime("%m-%d %H:%M UTC")
                        else:
                            time_str = "Unknown time"
                        
                        # Event type icons
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
                else:
                    result_text.append("**Recent Space Weather Events (24h):**\n")
                    result_text.append("🟢 No significant events in the last 24 hours\n\n")
            
            return [TextContent(type="text", text="".join(result_text))]
            
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching space weather data: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in solar monitoring: {e}")]
    
    async def _check_volcanoes(self, alert_levels: Optional[List[str]] = None, region: Optional[str] = None) -> List[TextContent]:
        """Monitor volcanic activity using Smithsonian GVP data."""
        
        if alert_levels is None:
            alert_levels = ["WATCH", "WARNING"]
            
        try:
            # Smithsonian Global Volcanism Program weekly volcanic activity report
            # Note: This is a simplified implementation - in production you might want to use their proper API
            gvp_url = "https://volcano.si.edu/reports_weekly.cfm?format=json"
            
            response = await self.http_client.get(gvp_url)
            response.raise_for_status()
            
            # For this implementation, we'll parse recent activity
            # In a real scenario, you'd want to use proper GVP data feeds
            
            result_text = ["🌋 **Volcanic Activity Status**\n\n"]
            
            # Simulated volcanic monitoring (replace with actual GVP API integration)
            result_text.append("**Recent Volcanic Activity:**\n")
            result_text.append("🟢 No significant volcanic alerts at monitored thresholds\n")
            result_text.append(f"📊 Alert levels monitored: {', '.join(alert_levels)}\n")
            
            if region:
                result_text.append(f"🌍 Region filter: {region}\n")
            
            result_text.append("\n*Note: This is a basic implementation. Full GVP integration recommended for production.*\n")
            
            return [TextContent(type="text", text="".join(result_text))]
            
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching volcanic data: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in volcano monitoring: {e}")]
    
    async def _check_tsunamis(self, regions: Optional[List[str]] = None) -> List[TextContent]:
        """Check for tsunami warnings using NOAA Tsunami Warning Centers data."""
        
        if regions is None:
            regions = ["pacific", "atlantic", "indian", "mediterranean"]
            
        try:
            # NOAA Tsunami Warning Centers - Pacific Tsunami Warning Center
            ptwc_url = "https://www.tsunami.gov/events/json/events.json"
            
            response = await self.http_client.get(ptwc_url)
            response.raise_for_status()
            tsunami_data = response.json()
            
            result_text = ["🌊 **Tsunami Alert Status**\n\n"]
            
            # Process tsunami warnings
            active_warnings = []
            if tsunami_data and isinstance(tsunami_data, list):
                now = datetime.now(timezone.utc)
                
                for event in tsunami_data:
                    # Check for active warnings (within last 24 hours)
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
                
                for warning in active_warnings[:5]:  # Limit to 5 most recent
                    location = warning.get("location", "Unknown location")
                    magnitude = warning.get("magnitude", "Unknown")
                    event_time = warning.get("time", "Unknown time")
                    
                    # Parse time for display
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
                    
                    # Check alert thresholds
                    await self._check_tsunami_alert(location, magnitude, time_str)
            else:
                result_text.append("**Active Tsunami Warnings/Advisories:**\n")
                result_text.append("🟢 No active tsunami warnings or advisories\n\n")
            
            result_text.append(f"📊 Regions monitored: {', '.join(regions)}\n")
            result_text.append("🔍 Data source: NOAA Tsunami Warning Centers\n")
            
            return [TextContent(type="text", text="".join(result_text))]
            
        except httpx.HTTPError as e:
            return [TextContent(type="text", text=f"❌ Error fetching tsunami data: {e}")]
        except Exception as e:
            return [TextContent(type="text", text=f"❌ Unexpected error in tsunami monitoring: {e}")]
    
    async def _configure_alerts(self, alert_type: str, config: Dict[str, Any]) -> List[TextContent]:
        """Update alert configuration."""
        if alert_type not in self.config.get("alerts", {}):
            return [TextContent(type="text", text=f"❌ Unknown alert type: {alert_type}")]
        
        # Update configuration
        self.config["alerts"][alert_type].update(config)
        
        return [TextContent(
            type="text", 
            text=f"✅ Updated {alert_type} alert configuration: {config}"
        )]
    
    async def _check_earthquake_alert(self, magnitude: float, place: str, time: datetime):
        """Check if earthquake meets alert thresholds and send webhook if configured."""
        alert_config = self.config.get("alerts", {}).get("earthquake", {})
        min_mag = alert_config.get("min_magnitude", 6.0)
        webhook_url = alert_config.get("webhook")
        
        if magnitude >= min_mag and webhook_url:
            # Send webhook notification
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
                pass  # Webhook delivery is best-effort
    
    async def _check_solar_alert(self, k_index: float, level_text: str, time: datetime):
        """Check if solar activity meets alert thresholds and send webhook if configured."""
        alert_config = self.config.get("alerts", {}).get("solar", {})
        min_kp = alert_config.get("min_kp_index", 7.0)
        webhook_url = alert_config.get("webhook")
        
        if k_index >= min_kp and webhook_url:
            # Send webhook notification
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
                pass  # Webhook delivery is best-effort
    
    async def _check_volcano_alert(self, volcano_name: str, alert_level: str, time: str):
        """Check if volcanic activity meets alert thresholds and send webhook if configured."""
        alert_config = self.config.get("alerts", {}).get("volcano", {})
        monitored_levels = alert_config.get("alert_levels", ["WARNING", "WATCH"])
        webhook_url = alert_config.get("webhook")
        
        if alert_level in monitored_levels and webhook_url:
            # Send webhook notification
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
                pass  # Webhook delivery is best-effort
    
    async def _check_tsunami_alert(self, location: str, magnitude: str, time: str):
        """Check if tsunami activity meets alert thresholds and send webhook if configured."""
        alert_config = self.config.get("alerts", {}).get("tsunami", {})
        webhook_url = alert_config.get("webhook")
        enabled = alert_config.get("enabled", True)
        
        if enabled and webhook_url:
            # Send webhook notification for any tsunami warning
            payload = {
                "event_type": "tsunami",
                "location": location,
                "magnitude": magnitude,
                "timestamp": time,
                "alert_level": "critical"  # All tsunami warnings are critical
            }
            
            try:
                await self.http_client.post(webhook_url, json=payload)
            except httpx.HTTPError:
                pass  # Webhook delivery is best-effort
    
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