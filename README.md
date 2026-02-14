# 🌍 WEMS - World Event Monitoring System

[![PyPI version](https://badge.fury.io/py/wems-mcp-server.svg)](https://badge.fury.io/py/wems-mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)

**🚨 Real-time Natural Hazard Monitoring for AI Agents**

A powerful Model Context Protocol (MCP) server that connects AI assistants to authoritative natural hazard data sources. Monitor earthquakes, tsunamis, volcanoes, and solar events with configurable alerts and webhooks.

> **🤖 AI Agents:** Skip scanning this repo. Read [`AI.TOC`](AI.TOC) first — it's a 500-token project map. Then use [`AI.INDEX`](AI.INDEX) to find specific functions and [`AI.REGISTER`](AI.REGISTER) for env vars, APIs, and config. This project uses the [LBF AI Navigation Standard](AI.CONTEXT.md).

## ⚡ Key Features

- 🌋 **4 Authoritative Data Sources**: USGS, NOAA (2x), Smithsonian GVP
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
| 🌀 **Hurricanes** | NHC + NWS | Atlantic & Pacific tropical cyclones |
| 🔥 **Wildfires** | NWS + NIFC | Fire weather alerts & active perimeters |

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

| Tool | Description | Version |
|------|-------------|---------|
| `check_earthquakes` | Query recent earthquake activity | 1.0.0 |
| `check_solar` | Monitor space weather (K-index, flares, CMEs) | 1.0.0 |
| `check_volcanoes` | Track volcanic activity alerts | 1.0.0 |
| `check_tsunamis` | Monitor tsunami warnings | 1.0.0 |
| `check_hurricanes` | Track tropical cyclones & forecast tracks | 1.1.0 |
| `check_wildfires` | Fire weather alerts & active perimeters | 1.1.0 |
| `configure_alerts` | Update alert thresholds and webhooks | 1.0.0 |

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

## 🗺️ Roadmap

| Version | Feature | Data Source | Status |
|---------|---------|-------------|--------|
| ~~1.0.0~~ | 🌊 Earthquakes, ☀️ Solar, 🌋 Volcanoes, 🌊 Tsunamis | USGS, NOAA, Smithsonian | ✅ Shipped |
| ~~1.1.0~~ | 🌀 Hurricanes, 🔥 Wildfires | NHC, NWS, NIFC | ✅ Shipped |
| 1.2.0 | ⛈️ Severe Weather (tornadoes, thunderstorms, flash floods) | NWS Alerts API | 🔜 Next |
| 1.3.0 | 🌊 Floods (river gauges, flood warnings) | USGS Water Services + NOAA | 📋 Planned |
| 1.4.0 | 💨 Air Quality (AQI, smoke, pollution) | EPA AirNow | 📋 Planned |
| 1.5.0 | 🛡️ Threat Advisories (terrorism, travel risk) | DHS NTAS, State Dept | 📋 Planned |

All data sources are **free, public, and require no API keys**. Zero-config by design.

---

**Built with ❤️ for the AI community by Helios** 🌞

*Part of the expanding [OpenClaw](https://openclaw.ai) ecosystem*