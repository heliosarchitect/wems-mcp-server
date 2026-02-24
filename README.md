# 🌍 WEMS - World Event Monitoring System

[![PyPI version](https://badge.fury.io/py/wems-mcp-server.svg)](https://badge.fury.io/py/wems-mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

<!-- mcp-name: io.github.heliosarchitect/wems -->

**🚨 Real-time Natural Hazard Monitoring for AI Agents**

A powerful Model Context Protocol (MCP) server that connects AI assistants to authoritative natural hazard data sources. Monitor earthquakes, tsunamis, volcanoes, and solar events with configurable alerts and webhooks.

> **🤖 AI Agents:** Skip scanning this repo. Read [`AI.TOC`](AI.TOC) first — it's a 500-token project map. Then use [`AI.INDEX`](AI.INDEX) to find specific functions and [`AI.REGISTER`](AI.REGISTER) for env vars, APIs, and config. This project uses the [LBF AI Navigation Standard](AI.CONTEXT.md).

## ⚡ Key Features

- 🌋 **9+ Authoritative Data Sources**: USGS, NOAA, Smithsonian GVP, NHC, NIFC, OpenAQ, DHS, State Dept, CISA, US Drought Monitor
- 🎯 **Real-time Monitoring**: Live data feeds with customizable thresholds
- 🔔 **Smart Alerts**: Webhook notifications for critical events
- 🗺️ **Geographic Filtering**: Target specific regions or global coverage
- 🔧 **Zero Configuration**: Works out-of-the-box, configure only what you need
- 🐳 **Production Ready**: Docker support, comprehensive error handling

### Natural Hazards Covered

| Hazard Type | Data Source | Coverage |
|-------------|-------------|----------|
| 🌊 **Earthquakes** | USGS | Global, magnitude filtering |
| 🌊 **Tsunamis** | NOAA PTWC + CTWC | Global ocean basins |
| 🌋 **Volcanoes** | Smithsonian GVP + USGS | Global volcanic activity |
| ☀️ **Solar Events** | NOAA SWPC | Solar flares, CMEs, geomagnetic storms |
| 🌞 **Space Weather Alerts** | NOAA SWPC | Active space weather alerts & warnings |
| 🌀 **Hurricanes** | NHC + NWS | Atlantic & Pacific tropical cyclones |
| 🔥 **Wildfires** | NWS + NIFC | Fire weather alerts & active perimeters |
| ⛈️ **Severe Weather** | NWS Alerts | Tornadoes, thunderstorms, floods, winter storms |
| 💨 **Air Quality** | OpenAQ | Global AQI, PM2.5, PM10, O₃, NO₂, SO₂, CO |
| 🌵 **Drought Conditions** | US Drought Monitor | US state drought levels (D0-D4) + trends |
| 🛡️ **Threat Advisories** | DHS NTAS + State Dept + CISA | Terrorism, travel risk, cyber threats |

## 🚀 Quick Start

### Install via PyPI (Recommended)

```bash
pip install wems-mcp-server
```

### Or install from source

```bash
git clone https://github.com/heliosarchitect/wems-mcp-server.git
cd wems-mcp-server
pip install -r requirements.txt
```

### Basic Usage

```bash
# Run as MCP server (connects to AI assistants)
python -m wems_mcp_server

# Test earthquake monitoring
python -c "
import asyncio
from wems_mcp_server import check_earthquakes
print(asyncio.run(check_earthquakes(min_magnitude=6.0)))
"
```

### One-command AI Alerting Setup (Relay + n8n)

```bash
bash scripts/setup_wems_alerting_ai.sh
```

This will:
- install/start `wems-unified-relay.service`
- upsert and activate the unified n8n ingest workflow
- wire tracker posting credentials automatically

### Example Output

```json
{
  "earthquakes_found": 3,
  "events": [
    {
      "magnitude": 7.2,
      "location": "67 km SW of Tres Picos, Mexico",
      "time": "2024-02-13T14:30:15Z",
      "depth": 35.8,
      "tsunami_threat": true
    }
  ]
}
```

## MCP Tools

| Tool | Description |
|------|-------------|
| `check_earthquakes` | Query recent earthquake activity |
| `check_solar` | Monitor space weather (K-index, flares, CMEs) |
| `check_volcanoes` | Track volcanic activity alerts |
| `check_tsunamis` | Monitor tsunami warnings |
| `check_hurricanes` | Track tropical cyclones & forecast tracks |
| `check_wildfires` | Fire weather alerts & active perimeters |
| `check_severe_weather` | Monitor tornadoes, thunderstorms, flash floods |
| `check_floods` | Flood warnings & USGS river gauge data |
| `check_air_quality` | AQI monitoring with pollutant data |
| `check_threat_advisories` | Terrorism, travel risk & cyber threat monitoring |
| `check_space_weather_alerts` | Active space weather alerts & warnings from NOAA SWPC |
| `check_drought_status` | US state drought conditions with D0-D4 levels (Premium) |
| `configure_alerts` | Update alert thresholds and webhooks |
| `fuse_multi_source_incidents` | Multi-source incident fusion (feature-flagged) |

## Configuration

```yaml
alerts:
  earthquake:
    min_magnitude: 6.0
    regions: ["US", "Caribbean", "Pacific"]
    webhook: "https://your-endpoint.com/earthquake"
  
  solar:
    min_kp_index: 7  # Geomagnetic storm threshold
    webhook: "https://your-endpoint.com/solar"
    
  volcano:
    alert_levels: ["WARNING", "WATCH"]
    webhook: "https://your-endpoint.com/volcano"
    
  tsunami:
    enabled: true
    regions: ["pacific", "atlantic", "indian"]
    webhook: "https://your-endpoint.com/tsunami"
```

## Data Sources

- USGS Earthquake Hazards Program
- NOAA Pacific Tsunami Warning Center
- NOAA Central Tsunami Warning Center  
- Smithsonian Global Volcanism Program
- NOAA Space Weather Prediction Center
- National Hurricane Center (NHC)
- National Interagency Fire Center (NIFC)
- NWS Alerts API
- OpenAQ (Global Air Quality)
- DHS National Terrorism Advisory System (NTAS)
- U.S. State Department Travel Advisories
- CISA Cybersecurity Advisories

## OpenClaw Integration

Add to your OpenClaw configuration:

```json
{
  "mcpServers": {
    "wems": {
      "command": "python3",
      "args": ["/path/to/wems-mcp-server/wems_mcp_server.py"],
      "env": {
        "WEMS_CONFIG": "/path/to/config.yaml"
      }
    }
  }
}
```

## 🎯 Use Cases

- **🏢 Enterprise Risk Management**: Automated threat assessment for global operations
- **📺 News Organizations**: Real-time natural disaster reporting and alerts  
- **🔬 Research Institutions**: Data collection for scientific analysis
- **🏠 Personal Safety**: Location-specific hazard monitoring for families
- **🤖 AI Emergency Response**: Integration with disaster response chatbots
- **📱 Alert Systems**: Custom notification workflows for critical events

## 🔧 Advanced Configuration

```yaml
# config.yaml - Full customization example
alerts:
  earthquake:
    min_magnitude: 6.0
    regions: ["US", "Caribbean", "Pacific"]
    webhook: "https://your-endpoint.com/earthquake"
    
  solar:
    min_kp_index: 7  # G3+ geomagnetic storm
    webhook: "https://your-endpoint.com/solar"
    
  volcano:
    alert_levels: ["WARNING", "WATCH"] 
    regions: ["Cascade Range", "Ring of Fire"]
    webhook: "https://your-endpoint.com/volcano"
    
  tsunami:
    enabled: true
    regions: ["pacific", "atlantic", "indian"]
    webhook: "https://your-endpoint.com/tsunami"
```

## 📊 Monitoring Dashboard

Pair with monitoring tools for comprehensive coverage:

```bash
# Example: Send earthquake data to monitoring system
curl -X POST https://your-monitoring.com/api/events \
  -H "Content-Type: application/json" \
  -d "$(python -c 'import wems; print(wems.get_recent_earthquakes())')"
```

## 💳 Billing & Monetization (Current)

WEMS now includes Stripe metering scaffolding and affordable default pricing.

### Current pricing defaults
- Free tier: **5,000 calls per rolling 30 days**
- 0–100,000 calls: **$0.0010/call**
- 100,001–500,000 calls: **$0.0008/call**
- 500,001+ calls: **$0.0006/call**

### Accessory call weights (default)
- Most tools: `1` unit
- `check_space_weather_alerts`: `2` units
- `fuse_multi_source_incidents`: `3` units

### Billing config
See: `config/wems_stripe_billing.json`

Key fields:
- `event_name`
- `api_key_to_customer`
- `billing_units.default`
- `billing_units.by_tool`
- `pricing.free_calls_per_rolling_30d`
- `pricing.tiers[]`

---

**Built with ❤️ for the AI community by Helios** 🌞

*Part of the expanding [OpenClaw](https://openclaw.ai) ecosystem*