# Changelog

All notable changes to the WEMS MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.12.0] - 2026-02-23

### Changed
- Default source cadence tuned for low-latency safety alerting:
  - `usgs_earthquake`: 15s
  - `volcano_feed`: 60s
  - `swpc_solar`: 60s
- Enabled `volcano_feed` by default.
- Added earthquake-triggered immediate volcano check in unified relay path.

### Fixed
- Unified relay config/state paths now point to canonical WEMS repo paths.

## [1.11.0] - 2026-02-23

### Added
- One-command AI/operator bootstrap: `scripts/setup_wems_alerting_ai.sh`.
  - Installs/starts unified relay systemd service.
  - Upserts + activates n8n unified ingest workflow automatically.
  - Injects Gitea token for tracker posting.

### Changed
- Version bump `1.10.0` → `1.11.0` for automated setup workflow.

## [1.10.0] - 2026-02-23

### Added
- User systemd service unit for unified relay: `systemd/wems-unified-relay.service`.
- Install helper script: `scripts/install_wems_unified_relay_service.sh`.
- Operations runbook: `docs/WEMS_ALERTING_RELAY_RUNBOOK.md`.

### Changed
- Version bump `1.9.0` → `1.10.0` for relay operational hardening.

## [1.9.0] - 2026-02-23

### Added
- **Near-real-time unified alerting integration assets** moved into WEMS canonical repo:
  - `scripts/wems_unified_relay.py` (adapter relay daemon)
  - `config/wems_alert_config.json` (user-configurable radii + thresholds)
  - `integrations/n8n/workflows/wems_unified_ingest_v2_6_0.json` (unified webhook ingest)
- User-configurable per-threat radii defaults (including active shooter and volcano examples).

### Changed
- Canonical ownership of WEMS alerting integration moved from cross-project pipeline workspace into `wems-mcp-server`.

## [1.8.1] - 2026-02-22

### Added
- **Feature Flagged Tool**: `fuse_multi_source_incidents` for multi-source confidence fusion (wems-041).
- New fusion engine to cluster co-temporal/co-spatial events and emit canonical incident objects.
- Confidence scoring with weighted source breakdown across USGS/NOAA/NWS/CISA.
- Preservation of source evidence (IDs, URLs, timestamps) in fused output.

### Changed
- Added environment feature flag parser and flag registry in server init:
  - `WEMS_FEATURE_MULTI_SOURCE_CONFIDENCE_FUSION` (default: disabled)

### Tests
- Added targeted test suite: `tests/test_confidence_fusion.py`.
- Full project test suite executed successfully.

## [1.3.0] - 2026-02-13

### Added
- **New Tool**: `check_floods` - Monitor flood warnings and river gauge data from USGS and NOAA
  - USGS Water Services API integration for river gauge monitoring (free, no API key required)
  - NOAA NWS flood-specific alerts (Flash Flood Warning, Flood Warning, Flood Watch, Flood Advisory)
  - Free tier: Major floods only, last 24h, 3 results max
  - Premium tier: All flood stages (action/minor/moderate/major), up to 7 days, state filtering, river gauge data, 25 results max
  - Filtering by: state, flood stage, time range, optional river gauge integration
  - Webhook alerts for major and moderate flood events
  - Comprehensive test coverage with 20+ flood-specific tests

### Technical Details
- Dual data source integration: NWS Alerts API + USGS Water Services API
- Intelligent flood stage mapping from NWS severity levels to standardized flood stages
- River gauge data with flood stage estimation based on gauge height
- Event-specific emoji coding and formatting (🔴🌊 for flash floods, 🟠🌊 for flood warnings, etc.)
- Follows existing tier-based access patterns with appropriate premium restrictions
- Full webhook integration for emergency flood notifications

## [1.2.0] - 2026-02-13

### Added
- **New Tool**: `check_severe_weather` - Monitor severe weather alerts from the National Weather Service
  - Supports tornadoes, thunderstorms, flash floods, winter storms, and more
  - Free tier: Last 24h, extreme/severe severity only, 3 results max
  - Premium tier: Up to 7 days, all severity levels, state filtering, 25 results max
  - Filtering by: state, severity, event type, urgency, certainty
  - Webhook alerts for tornado warnings and extreme weather events
  - Comprehensive test coverage with 147+ tests

### Technical Details
- Uses NWS Alerts API (https://api.weather.gov/alerts) - no API key required
- Follows the same tier-based access patterns as existing tools
- Filters out test messages and applies time-based filtering
- Emoji-coded severity indicators and event-specific icons
- Webhook integration for emergency notifications

## [1.1.1] - 2026-02-13

### Fixed
- Minor packaging improvements and metadata updates

## [1.1.0] - 2026-02-13

### Added
- Hurricane and tropical storm monitoring (`check_hurricanes`)
- Wildfire activity and fire weather alerts (`check_wildfires`)
- Enhanced error handling across all tools
- Comprehensive test suite with 100+ tests

### Improved
- Better tier-based access control
- Enhanced webhook alert configurations
- Improved documentation and examples

## [1.0.0] - 2026-02-13

### Added
- Initial release with core monitoring tools:
  - Earthquake monitoring (`check_earthquakes`)
  - Solar/space weather monitoring (`check_solar`)
  - Volcanic activity monitoring (`check_volcanoes`)
  - Tsunami alert monitoring (`check_tsunamis`)
- Tier-based access system (free/premium)
- Webhook alert configuration
- MCP server compatibility
- Comprehensive documentation

### Technical Features
- Async HTTP client with proper error handling
- YAML configuration support
- Environment-based tier detection
- Rate limiting and result pagination
- Professional logging and monitoring