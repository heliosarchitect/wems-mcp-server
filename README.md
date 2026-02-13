# WEMS - World Event Monitoring System

A Model Context Protocol (MCP) server for monitoring natural hazards and world events.

## Features

- **Earthquakes**: Real-time USGS data with magnitude filtering
- **Tsunamis**: NOAA Tsunami Warning Centers
- **Volcanoes**: Smithsonian Global Volcanism Program + USGS
- **Solar Events**: NOAA Space Weather (flares, CMEs, Kp index)
- **Configurable Webhooks**: Push notifications at custom thresholds
- **Geographic Filtering**: Region-specific monitoring

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure alerts
cp config.example.yaml config.yaml
# Edit config.yaml with your thresholds and webhooks

# Run as MCP server
python wems_mcp_server.py

# Or standalone
python -m wems.cli check-earthquakes --min-magnitude 6.0
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

Built for the OpenClaw ecosystem by Helios 🌞