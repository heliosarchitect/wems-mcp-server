# wems-041 requirements (finalized)

## Objective
Blend overlapping events from USGS/NOAA/NWS/CISA into a canonical incident with a confidence score and source attribution.

## Functional Requirements
1. Accept multiple source events containing at least: `source`, `timestamp`, `latitude`, `longitude`.
2. Normalize source names to lower-case and support only: `usgs`, `noaa`, `nws`, `cisa`.
3. Cluster events into one incident if BOTH are true:
   - temporal delta <= `fusion_window_minutes` (default 30)
   - spatial distance <= `dedupe_radius_km` (default 25)
4. Output one incident object per cluster with:
   - stable incident id
   - confidence score in range `[0, 1]`
   - confidence breakdown by source weight
   - evidence list preserving source IDs/URLs/timestamps
5. Source weight model defaults:
   - usgs: 1.00
   - noaa: 0.90
   - nws: 0.95
   - cisa: 0.85
6. Feature must be **fully gated** by env flag:
   - `WEMS_FEATURE_MULTI_SOURCE_CONFIDENCE_FUSION`
   - default `false`

## Non-Functional Requirements
- No behavior change to existing tools when flag is off.
- Invalid/unsupported events must be ignored, not crash processing.
- Deterministic sorting: incidents ordered by descending confidence.

## Acceptance Criteria
- New tests verify clustering, confidence calculation, and flag behavior.
- Existing test suite remains green.
- No tool appears in list/call path unless feature flag is enabled.
