# Changelog

All notable changes to the WEMS MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.13.9] - 2026-02-24

### Changed
- Earthquake relay summaries now use escalation tiers:
  - M7.0+ → `🚨 MAJOR EARTHQUAKE ALERT`
  - M8.0+ → `🟥 EXTREME EARTHQUAKE ALERT`
- Added structured severity mapping (`medium`/`high`/`critical`) in unified relay payload for stronger downstream alert routing.

## [1.13.8] - 2026-02-24

### Fixed
- `configure_alerts` now supports all implemented hazard families (earthquake, solar, volcano, tsunami, hurricane, wildfire, severe_weather, floods, air_quality, threat_advisories, space_weather_alerts, drought_status).
- Alert config schema enum expanded to full supported set.
- Default config bootstrap now includes alert buckets for all hazard families.
- Added regression coverage in `tests/test_configure_alerts.py` for newly supported alert types.

## [1.13.7] - 2026-02-23

### Added
- Trial lifecycle conversion hooks (`wems_trial_messaging.py`) for day-3/day-10/day-13 touchpoints.
- New safe-default config: `config/wems_trial_messaging.json`.
- Quiet-hours guard and per-tenant dedupe state for lifecycle messaging.
- Test coverage for touchpoint dispatch, quiet-hours suppression, and disabled-default behavior (`tests/test_trial_messaging.py`).

### Changed
- Wired best-effort trial lifecycle hook emission into successful tool-call path (non-blocking).
- Updated docs with lifecycle hook configuration and env toggles.

## [1.13.6] - 2026-02-23

### Changed
- Removed provider-specific 1Password (`op://`) key resolution from application code.
- Stripe billing now reads keys from standard env vars only: `STRIPE_API_KEY` / `STRIPE_SECRET_KEY`.
- Keeps app layer provider-agnostic; secret manager integration is runtime/deployment responsibility.

### Docs
- Removed 1Password-specific billing config/runtime examples from README.

## [1.13.4] - 2026-02-23

### Fixed
- Updated `README.md` to reflect current shipping features and monetization state for GitHub and PyPI.
- Removed stale per-tool version column and outdated roadmap-complete messaging.
- Added current billing defaults, rolling 30-day free window, and accessory unit weighting documentation.

## [1.13.3] - 2026-02-23

### Added
- Accessory/weighted call billing units via `billing_units` config.
- `units_for_tool(tool_name)` helper to map tool calls to billable units.

### Changed
- Stripe meter emission now uses per-tool units instead of constant `1`.
- Added default weights in `config/wems_stripe_billing.json`:
  - most checks = 1 unit
  - `check_space_weather_alerts` = 2 units
  - `fuse_multi_source_incidents` = 3 units

## [1.13.2] - 2026-02-23

### Changed
- Free tier billing window updated to **rolling 30-day** semantics.
- Billing config key updated to `pricing.free_calls_per_rolling_30d` (with backward-compatible fallback to `free_calls_per_month`).
- Cost estimator now uses rolling-window input: `estimate_monthly_cost(total_calls_rolling_30d)`.

## [1.13.1] - 2026-02-23

### Changed
- Added affordable default pricing tiers to Stripe billing config (`config/wems_stripe_billing.json`):
  - Free: 5,000 calls/month
  - Up to 100,000 calls: $0.0010/call
  - 100,001–500,000 calls: $0.0008/call
  - 500,001+ calls: $0.0006/call
- Added `estimate_monthly_cost(total_calls)` helper in `wems_stripe_billing.py` for deterministic tier-cost previews.

## [1.13.0] - 2026-02-23

### Added
- Stripe metering scaffold for per-call billing (`wems_stripe_billing.py`).
- Best-effort meter event emission on successful tool calls (does not block alerting path).
- New billing config template: `config/wems_stripe_billing.json`.

### Configuration
- `WEMS_STRIPE_BILLING_ENABLED=1` to enable metering.
- `STRIPE_API_KEY` / `STRIPE_SECRET_KEY` for Stripe auth.
- `WEMS_STRIPE_BILLING_CONFIG` optional override for config path.

## [1.12.3] - 2026-02-23

### Fixed
- Fixed packaged console script entrypoint by using a synchronous `main()` wrapper that executes async runtime via `asyncio.run(...)`.
- Added minimal `--help` / `-h` handling for `wems` CLI to prevent coroutine warnings and provide usable output.

### Packaging
- Included operational relay assets in PyPI artifact via setuptools data-files:
  - `config/wems_alert_config.json`
  - `scripts/setup_wems_alerting_ai.sh`
  - `scripts/install_wems_unified_relay_service.sh`
  - `scripts/wems_unified_relay.py`
  - `systemd/wems-unified-relay.service`
  - `docs/WEMS_ALERTING_RELAY_RUNBOOK.md`

## [1.12.2] - 2026-02-23

### Fixed
- Restored deterministic alert parsing behavior for CI fixture compatibility:
  - Severe weather no longer hard-filters by local sent-time cutoff when using active NWS feed.
  - Flood alert ingestion no longer hard-filters by local sent-time cutoff.
  - NTAS advisories are no longer hard-dropped by local expiration clock.
- Resolves current failing test groups in floods, severe weather, and threat advisories.

## [1.12.1] - 2026-02-23

### Fixed
- Restored missing runtime modules required by imports:
  - `wems_rate_limit.py`
  - `wems_usage.py`
  - `wems_license.py`
- Updated setuptools module packaging so these files ship in builds/wheels.
- Fixes CI/PyPI publish failure (`ModuleNotFoundError: wems_rate_limit`).

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