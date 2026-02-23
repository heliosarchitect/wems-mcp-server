# wems-041 design

## Incremental Strategy
Implement confidence fusion as an isolated, feature-flagged path so default server behavior remains unchanged.

## Architecture
- Add feature-flag registry in `WemsServer.__init__`.
- Add helper methods:
  - `_env_flag()` for boolean env parsing
  - `_distance_km()` for geospatial dedupe (Haversine)
  - `_fuse_events_to_incidents()` for clustering + scoring
- Add optional MCP tool registration/call routing:
  - `fuse_multi_source_incidents` (only when flag enabled)

## Data Flow
1. Receive event array input.
2. Validate each event: source in allowed set + parseable timestamp + coordinates.
3. Cluster by first-match against existing cluster representative using time + distance thresholds.
4. Aggregate per cluster:
   - source set and weighted confidence
   - centroid location
   - first/last seen timestamps
   - source evidence records
5. Return JSON payload with incidents sorted by confidence descending.

## Backward Compatibility
- Feature is invisible unless `WEMS_FEATURE_MULTI_SOURCE_CONFIDENCE_FUSION=true`.
- Existing tool behavior and schemas untouched when flag is false.

## Risks / Mitigations
- Risk: over-clustering dense incidents.
  - Mitigation: configurable window/radius parameters.
- Risk: malformed upstream event payloads.
  - Mitigation: strict validation + skip invalid records.
