# WEMS (World Event Monitoring System) — Version Forensics

## Current State
**VERSION**: v1.7.3 (Space Weather + Drought Monitor)  
**DEPLOYMENT**: Production MCP server, published to PyPI  
**LAST COMMIT**: `da81f61` - Space weather alerts and drought monitoring  
**DATE**: 2026-02-14  

## Active Features with Behavioral Signatures

### FEATURE: "Space Weather Monitoring" (v1.7.3)
**ADDED IN**: v1.7.3 (2026-02-14)

**BEHAVIORAL SIGNATURE**:
- Log pattern: NOAA Space Weather API calls to `swpc.noaa.gov/json/`
- Tool call sequence: `space_weather_alerts` → NOAA API → solar activity parsing
- Response pattern: Returns geomagnetic storm levels (G1-G5), solar flare data
- Failure mode: NOAA API downtime returns empty alerts array

**IMPLEMENTS**:
- Changes to: Added space weather monitoring module
- Adds decision branch: Solar activity threat assessment
- Modifies priority: Critical infrastructure alerts for solar events

**DEBUGGING HOOKS**:
- If you see `swpc.noaa.gov` in logs → feature active
- If no space weather data for >6 hours → NOAA API issue
- Rollback test: Remove space weather tool, does core WEMS still work?

**ROLLBACK PLAN**:
- Comment out space weather tool registration in `wems_server.py`
- Side effects: No solar storm alerts
- Fallback behavior: v1.6.x without space weather capability

**INTERACTS WITH**:
- Depends on: NOAA Space Weather Prediction Center API
- Conflicts with: None (isolated tool)
- Modifies behavior of: Alert priority weighting (space weather = high priority)

---

### FEATURE: "US Drought Monitor Integration" (v1.7.3)
**ADDED IN**: v1.7.3 (2026-02-14)

**BEHAVIORAL SIGNATURE**:
- Log pattern: Drought Monitor API calls to `droughtmonitor.unl.edu`
- Tool call sequence: `drought_monitor` → UNL API → drought severity mapping
- Response pattern: Returns D0-D4 drought categories with geographic data
- Failure mode: University API rate limits return HTTP 429

**IMPLEMENTS**:
- Changes to: Added drought monitoring capability
- Adds decision branch: Agricultural/water supply risk assessment  
- Modifies priority: Long-term environmental threat tracking

**DEBUGGING HOOKS**:
- If you see `droughtmonitor.unl.edu` in logs → feature active
- If HTTP 429 errors → rate limiting active, need backoff
- Rollback test: Disable drought tool, verify other monitoring continues

**ROLLBACK PLAN**:
- Remove drought monitor tool from server registration
- Side effects: No agricultural drought alerts
- Fallback behavior: v1.6.x environmental monitoring only

---

### FEATURE: "Threat Advisory System" (v1.5.0)
**ADDED IN**: v1.5.0 (2026-01-xx)

**BEHAVIORAL SIGNATURE**:
- Log pattern: Multi-source aggregation with threat level calculations
- Tool call sequence: Multiple APIs → threat scoring → priority ranking
- Response pattern: Returns unified threat assessment with confidence scores
- Failure mode: Single API failure reduces overall threat accuracy

**IMPLEMENTS**:
- Changes to: Cross-correlation of multiple threat sources
- Adds decision branch: Unified vs individual source reporting
- Modifies priority: Comprehensive situational awareness

**DEBUGGING HOOKS**:
- If you see threat correlation calculations → feature active
- If threat levels seem inconsistent → API source reliability issue
- Check: Individual tool outputs vs aggregated threat assessment

**ROLLBACK PLAN**:
- Revert to individual tool reporting (v1.4.x behavior)
- Side effects: No cross-source threat correlation
- Fallback behavior: Independent tool responses

---

### FEATURE: "Air Quality Monitoring" (v1.4.0)
**ADDED IN**: v1.4.0 (2026-01-xx)

**BEHAVIORAL SIGNATURE**:
- Log pattern: EPA AirNow + OpenAQ API calls for AQI data
- Tool call sequence: `air_quality` → EPA/OpenAQ APIs → AQI calculation  
- Response pattern: Returns PM2.5, PM10, O3 levels with health recommendations
- Failure mode: API outages return stale or missing AQI data

**IMPLEMENTS**:
- Changes to: Real-time air quality health alerts
- Adds decision branch: Multi-source AQI validation
- Modifies priority: Public health environmental monitoring

**DEBUGGING HOOKS**:
- If you see `airnowapi.org` or OpenAQ calls → feature active
- If AQI data >6 hours old → API refresh failing
- Rollback test: Disable air quality, check other environmental tools

**ROLLBACK PLAN**:
- Remove air quality tools from MCP server registration
- Side effects: No particulate matter health alerts
- Fallback behavior: v1.3.x weather/disaster focus only

---

### FEATURE: "Hurricane Tracking" (v1.2.0-1.3.x)
**ADDED IN**: v1.2.0

**BEHAVIORAL SIGNATURE**:
- Log pattern: NOAA Hurricane Database + NHC active storm tracking
- Tool call sequence: `hurricane_monitor` → NOAA APIs → storm path modeling
- Response pattern: Returns active storms with projected paths, wind speeds
- Failure mode: Storm season API load causes timeouts

**IMPLEMENTS**:
- Changes to: Real-time tropical cyclone monitoring
- Adds decision branch: Active vs historical storm analysis
- Modifies priority: Immediate evacuation-level threat detection

**DEBUGGING HOOKS**:
- If you see `nhc.noaa.gov` API calls → feature active
- If no storm data during active season → API connectivity issue
- Hurricane season: June-November (high API usage expected)

**ROLLBACK PLAN**:
- Disable hurricane tracking module
- Side effects: No tropical storm alerts
- Fallback behavior: v1.1.x earthquake/wildfire focus

---

## Feature Interaction Map

```
Base MCP Server (v1.0) ←─── All Monitoring Tools
    ↓                         ↓
Earthquake (v1.0) ──→ Hurricane (v1.2) ──→ Wildfire (v1.2)
    ↓                    ↓                    ↓
Air Quality (v1.4) ──→ Threat Advisory (v1.5) ──→ Space Weather (v1.7.3)
    ↓                                             ↓
Drought Monitor (v1.7.3) ─────────────────────────┘

AMPLIFIES: Threat Advisory + All Sources = Comprehensive risk assessment
CONFLICTS: High API usage during disasters can cause rate limiting
GATES: Base MCP server stability affects all monitoring tools
```

## Rollback Sequence (v1.7.3 → v1.5.0)

**IMMEDIATE** (If new features break):
1. Check MCP server status: `python -m wems_mcp_server`
2. Test basic tools: earthquake, hurricane, wildfire
3. Verify API connectivity with simple curl tests

**SYSTEMATIC ROLLBACK**:
1. **Disable New Tools** → Comment out space_weather, drought_monitor in server.py
2. **Remove Dependencies** → Uninstall space weather API libraries  
3. **Revert API Calls** → Remove new endpoint integrations
4. **Test Core Function** → Verify original 8 tools still work

**VERIFICATION**:
- MCP server starts without errors
- Core monitoring tools respond within 5s
- No new API dependencies in requirements

## Bug Fix Chain Documentation

### BUG: API Endpoint Authentication (v1.5.1-1.5.2)
**DISCOVERED**: v1.5.1/1.5.2 releases  
**IMPACT**: 3 broken endpoints (tsunami, hurricane, air quality)  

**ROOT CAUSE ANALYSIS**:
1. **API Changes**: External providers modified authentication requirements
2. **Detection**: Tools returning HTTP 401/403 errors consistently
3. **Impact**: 31/31 integration tests passing but live queries failing
4. **Evidence**: Error logs showing authentication failures

**FIX DESCRIPTION**:
- Updated API key handling for affected endpoints
- Added authentication retry logic
- Verified all 31 integration tests + live API validation

**DEBUGGING PATH**:
```bash
# Test individual API endpoints
curl -H "Authorization: Bearer $API_KEY" https://tsunami.gov/api/alerts

# Check error patterns in logs  
grep "401\|403\|auth" ~/.openclaw/logs/wems.log

# Verify API key configuration
python -c "import os; print('API keys:', [k for k in os.environ if 'API' in k])"
```

**VERIFICATION**:
- Before: 3 tools consistently returning auth errors
- After: All tools return valid data within API rate limits
- Log change: No more authentication error messages

---

### BUG: CI/CD Pipeline Failures (v1.5.x)
**DISCOVERED**: Multiple releases  
**IMPACT**: PyPI uploads failing, version inconsistencies  

**ROOT CAUSE**: GitHub Actions workflow configuration issues
**FIX**: Fixed CI triggers, container images, and PyPI authentication

**DEBUGGING PATH**:
```bash
# Check GitHub Actions status
gh workflow list --repo heliosarchitectlbf/wems-mcp-server

# Verify PyPI package integrity
pip install --index-url https://test.pypi.org/simple/ wems-mcp-server
```

---

## Production Incident Response

### MCP Server Won't Start
**SYMPTOMS**: Server initialization fails, import errors
**LOG SIGNATURE**: `ModuleNotFoundError`, `ImportError` in startup logs
**IMMEDIATE ACTION**: Check Python dependencies, verify MCP library versions
**ESCALATION**: If core MCP framework incompatibility

### API Rate Limiting 
**SYMPTOMS**: HTTP 429 errors, empty responses from monitoring tools
**LOG SIGNATURE**: `429 Too Many Requests` in API call logs
**ACTION**: Implement exponential backoff, reduce polling frequency
**FALLBACK**: Use cached data with staleness warnings

### Space Weather API Downtime
**SYMPTOMS**: Empty space weather alerts during active solar events
**LOG SIGNATURE**: `Connection timeout` or HTTP 5xx from `swpc.noaa.gov`
**ACTION**: Switch to backup space weather sources or return cached alerts
**ESCALATION**: If NOAA SWPC infrastructure down >4 hours

### Drought Monitor API Changes
**SYMPTOMS**: Parsing errors from drought monitoring tool
**LOG SIGNATURE**: JSON parsing failures, unexpected response format
**ACTION**: Check UNL Drought Monitor API documentation for format changes
**ROLLBACK**: Disable drought monitoring temporarily

## Forensic Queries (6 months from now)

```bash
# Find which version introduced a feature
git log --oneline --grep="space.weather"
git log --oneline --grep="drought"  

# Verify server functionality
python -c "from wems_mcp_server import WemsServer; print('✓ Server imports OK')"

# Test individual tool responses
python -m wems_mcp_server --test-tool space_weather_alerts
python -m wems_mcp_server --test-tool drought_monitor

# Check API connectivity
curl -s "https://services.swpc.noaa.gov/json/notifications.json" | head
curl -s "https://droughtmonitor.unl.edu/DmData/GISData.aspx" -I

# Verify PyPI package
pip show wems-mcp-server | grep Version
pip install --dry-run --upgrade wems-mcp-server

# Debug rate limiting
grep "429\|rate.limit" ~/.openclaw/logs/wems.log | tail -10
```

## MCP Server Health Check

```bash
#!/bin/bash
# Health check script for WEMS MCP server

echo "=== WEMS MCP SERVER HEALTH CHECK ==="

# 1. Server startup test
echo "Testing server startup..."
timeout 10s python -m wems_mcp_server --version 2>/dev/null && echo "✓ Server starts" || echo "✗ Server startup failed"

# 2. Core tools test
echo "Testing core monitoring tools..."
TOOLS=("earthquake_monitor" "hurricane_monitor" "wildfire_monitor" "air_quality")
for tool in "${TOOLS[@]}"; do
    if python -c "from wems_mcp_server import WemsServer; s=WemsServer(); print('✓ $tool available')" 2>/dev/null; then
        echo "✓ $tool"  
    else
        echo "✗ $tool failed"
    fi
done

# 3. API connectivity
echo "Testing API endpoints..."
curl -s --max-time 5 "https://services.swpc.noaa.gov/json/notifications.json" >/dev/null && echo "✓ NOAA Space Weather" || echo "✗ NOAA Space Weather timeout"
curl -s --max-time 5 "https://droughtmonitor.unl.edu/DmData/GISData.aspx" -I >/dev/null && echo "✓ Drought Monitor" || echo "✗ Drought Monitor timeout"

# 4. Package integrity
INSTALLED=$(pip show wems-mcp-server 2>/dev/null | grep Version | cut -d' ' -f2)
LATEST=$(pip index versions wems-mcp-server 2>/dev/null | head -1 | cut -d' ' -f2)
echo "Installed: $INSTALLED, Latest: $LATEST"

echo "=== END HEALTH CHECK ==="
```

## Version Evolution Timeline

```
v1.0.0  ── Base MCP server + earthquake monitoring
v1.1.0  ── Added tsunami alerts  
v1.2.0  ── Hurricane + wildfire monitoring
v1.3.x  ── Stability fixes, improved error handling
v1.4.0  ── Air quality monitoring (EPA + OpenAQ)
v1.5.0  ── Threat advisory system (multi-source correlation)
v1.5.1-2 ── API authentication fixes
v1.6.x  ── Performance optimization
v1.7.3  ── Space weather + drought monitoring (CURRENT)
```

## Known Limitations & Workarounds

### API Rate Limits
- **NOAA**: 1000 requests/hour during storm season  
- **EPA AirNow**: 500 requests/hour
- **Workaround**: Implement caching with 15-minute refresh intervals

### Geographic Coverage  
- **US-focused**: Most APIs optimized for US locations
- **International**: Limited coverage for global events
- **Workaround**: Add international API sources in future versions

### Real-time vs Batch Processing
- **Current**: Individual API calls per tool request
- **Limitation**: Latency during high-usage periods  
- **Future**: Background polling with cached responses

---

*Generated by Helios VERSION_FORENSICS framework — searchable, greppable, debuggable.*  
*When WEMS breaks: run health check first, then debug specific API endpoints.*