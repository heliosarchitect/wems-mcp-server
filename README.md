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
| 🌊 **Tsunamis** | NOAA Pacific + Central Warning Centers | Global ocean basins |
| 🌋 **Volcanoes** | Smithsonian GVP + USGS | Global volcanic activity |
| ☀️ **Solar Events** | NOAA Space Weather | Solar flares, CMEs, geomagnetic storms |

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

- `check_earthquakes` - Query recent earthquake activity ✅
- `check_solar` - Monitor space weather events (K-index, solar flares, CMEs) ✅
- `check_volcanoes` - Track volcanic activity alerts ✅ NEW!
- `check_tsunamis` - Monitor tsunami warnings ✅ NEW!
- `configure_alerts` - Update alert thresholds and webhooks ✅

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

---

**Built with ❤️ for the AI community by Helios** 🌞

*Part of the expanding [OpenClaw](https://openclaw.ai) ecosystem*