# Real-Data Integration Plan — Agentic Golf Caddy

Document version: 1.0 · Date: 2026-04-15  
Owner: Alex Cannon  
Status: Proposed — ready for phased execution

## 1. Executive Summary

The Agentic Golf Caddy currently runs an 8-agent pipeline (InputInterpreter → Clarification → Context → Decision → AdaptiveStrategy → Coach → Verifier, orchestrated by `agents/pipeline.py`) on synthetic scenarios and skill-based default player profiles. All inputs — distance, wind, elevation, lie, pin — are either typed in by the user or copied from a `Scenario` dataclass in `ui/scenarios.py`. Player "tendencies" are derived on the fly from a mostly-empty `shot_feedback.json` via `FeedbackManager`.

The `data/` directory, `utils/` package, and `FeedbackManager` were designed as explicit integration hooks. This plan activates those hooks so that:

- Environmental inputs (wind, temperature, elevation) are fetched from authoritative public APIs instead of typed manually.
- Player profiles are learned from real launch-monitor and phone-app exports instead of being a static skill preset.
- Course geometry and hazards are sourced from OpenStreetMap so `ContextAgent` and `AdaptiveStrategyAgent` can reason about real holes.
- Recommendations are evaluated against a dataset of real shots, not only hand-written benchmarks.

The principle is hybrid real-data: authoritative free/public sources for v1, paid/commercial providers only where free data is insufficient (pin positions, tour-grade course catalogs).

## 2. Current State (baseline)

| Area | Status | Evidence |
|---|---|---|
| Agents | 8 agents wired into `Pipeline` | `agents/__init__.py` |
| Models | `ShotContext`, `ShotIntent`, `PlayerProfile`, `ShotFeedback`, `PlayerTendencies`, `CaddyDecision`, `AdaptiveDecision`, `CandidateOption`, `VerificationResult` | `models/` |
| Player data | 4 static skill profiles; `FeedbackManager` appends `ShotFeedback` entries to `data/shot_feedback.json` | `utils/feedback_manager.py` |
| Environment data | None — user types wind, temp, elevation into form or describes in free text | `app.py` structured tab |
| Course data | None — no course, hole, green, bunker, or water representation | — |
| Pin data | Enum `front/middle/back` only | `ShotContext.pin_position` |
| Evaluation | 3 benchmark JSON files (~45 deterministic cases + adaptive + clarification scenarios) | `benchmarks/` |
| Tests | 92 tests / 22 files | `tests/` |

Integration hooks already present: empty `data/` directory, `utils/` package structure, frozen Pydantic models that can be extended with new fields, `PipelineLogger` for structured capture.

## 3. Data Strategy

- Free first. Open-Meteo, USGS EPQS, OpenStreetMap/Overpass, and Nominatim cover 90% of v1 needs at $0.
- Cache aggressively. Every external call writes to a timestamped JSON cache under `data/cache/<source>/` keyed by `(lat, lon, timestamp-bucket)`. This makes tests reproducible and respects rate limits.
- Normalize at the boundary. Each source has an importer module that returns a Pydantic model; agents never see raw API payloads.
- Manual override always available. Every real-data field retains its current manual-entry path so the app works offline and the LLM can still be prompted with structured input.
- No scraping of restricted sources. No Google Maps tile scraping, no scraping pin-sheet PDFs without rights, no tour-course scraping.

## 4. Phased Plan

### Phase 1 — Environmental Data Connectors

Goal: replace manual wind/temperature/elevation entry with live public data.

New modules (under `utils/data_sources/`, new package):

| File | Responsibility | Source |
|---|---|---|
| `weather.py` | `get_weather(lat, lon, when=None) -> WeatherObservation` | Open-Meteo Forecast API (`api.open-meteo.com/v1/forecast`) |
| `elevation.py` | `get_elevation(lat, lon) -> float` and `get_elevation_delta(p1, p2)` | USGS EPQS (`epqs.nationalmap.gov/v1/json`) |
| `geocode.py` | `geocode(query) -> LatLon`; respects Nominatim's 1-req/sec limit | Nominatim |
| `cache.py` | Disk-backed memoization to `data/cache/<source>/` | Local |

New model (`models/environment.py`):

```python
class WeatherObservation(BaseModel, frozen=True):
    wind_speed_mph: float
    wind_direction_deg: float        # 0=N, 90=E
    temperature_f: float
    humidity_pct: float | None
    pressure_mb: float | None
    source: Literal["open-meteo", "noaa", "manual"]
    observed_at: datetime
```

Agent integration: `ContextAgent.run` accepts an optional `WeatherObservation` and an optional `(lat, lon)` tuple. If a coordinate is provided and manual wind fields are blank, it calls `get_weather()` and converts `wind_direction_deg + shot azimuth` into the existing `headwind`/`tailwind`/`crosswind_*` enum.

UI change: `app.py` gains a new "Location" expander with three inputs — course-name search (→ Nominatim → lat/lon), or raw lat/lon, or "use manual weather". A "Fetch live conditions" button populates wind/temp fields.

Acceptance criteria

- `pytest tests/data_sources/test_weather.py` passes with a VCR-style fixture.
- A Streamlit form with coords + "fetch" auto-fills `wind_speed` within ±1 mph of the Open-Meteo response.
- Cache hit on the second call within the same 15-minute bucket (no network).

### Phase 2 — Player Shot Importers and Real Tendencies

Goal: let a user upload their own TrackMan / Foresight / Golf Pad data, turn it into a `PlayerProfile` and `PlayerTendencies`, and feed that into `DecisionAgent` and `AdaptiveStrategyAgent`.

New modules (under `utils/importers/`):

| File | Input format | Output |
|---|---|---|
| `trackman.py` | TrackMan CSV (session export) | `list[ShotEvent]` |
| `foresight.py` | Foresight FSX CSV | `list[ShotEvent]` |
| `golfpad.py` | Golf Pad CSV round export | `list[ShotEvent]` |
| `normalizer.py` | `build_profile_from_shots(shots) -> PlayerProfile`, `build_tendencies(shots) -> PlayerTendencies` | — |

New model (`models/shot_event.py`):

```python
class ShotEvent(BaseModel, frozen=True):
    player_id: str
    club: str
    carry_yds: float
    total_yds: float
    launch_speed_mph: float | None
    spin_rpm: float | None
    offline_ft: float | None          # negative = left
    lie: LieType | None
    source: Literal["trackman","foresight","golfpad","manual"]
    captured_at: datetime
```

Storage: normalized shots written to `data/players/<player_id>/shots.parquet` (or JSONL fallback if `pyarrow` not installed). Profile + tendencies rebuilt from the full history on each import.

Club distances rebuild: per-club median carry, trimmed 10%-ile on both ends. Confidence-by-club = `1 - stdev/mean` clamped to `[0.2, 0.95]`. Common miss: majority label over `offline_ft` sign + magnitude threshold.

`FeedbackManager` migration: the existing `ShotFeedback` (user-reported post-shot) becomes a secondary signal layered onto the launch-monitor baseline — it does not replace it.

UI change: new sidebar section "Upload my shots" with a file uploader accepting `.csv`, detects format by header signature, shows preview + "Save as profile" button.

Acceptance criteria

- Loading a 200-row TrackMan CSV produces a `PlayerProfile` with ≥8 clubs and passes existing `Pipeline.run()`.
- `tests/importers/test_trackman.py`, `test_foresight.py`, `test_golfpad.py` all pass with fixture CSVs checked into `tests/fixtures/imports/`.
- Recommendations differ between a "default intermediate" profile and an uploaded real one for the same shot context (regression test).

### Phase 3 — Course & Hazard Model

Goal: give the pipeline a real `course`/`hole` object so `AdaptiveStrategyAgent` can reason about water, bunkers, and hole layout instead of a free-text `hazard_note`.

New modules (under `utils/data_sources/`):

- `overpass.py` — `fetch_course(osm_id) -> CoursePayload` running Overpass QL queries for `leisure=golf_course`, `golf=hole|green|fairway|bunker|water_hazard|tee`.
- `osm_parser.py` — converts Overpass GeoJSON into the model below.

New model (`models/course.py`):

```python
class Course(BaseModel, frozen=True):
    id: str
    name: str
    location: LatLon
    holes: list[Hole]

class Hole(BaseModel, frozen=True):
    number: int
    par: int
    tees: list[TeeBox]
    fairway_polygon: list[LatLon]
    green: Green
    hazards: list[Hazard]             # bunker / water / OB

class Hazard(BaseModel, frozen=True):
    kind: Literal["bunker","water","ob","trees"]
    polygon: list[LatLon]
    carry_distance_yds: float | None
```

Storage: `data/courses/<course_id>.json` (one file per course, immutable after ingest). A simple `courses/index.json` lists available courses.

Agent integration: `ContextAgent` gains optional `course_id + hole_number + tee_lat_lon`. When present, it derives `distance_to_target`, `hazard_note`, and `target_mode` geometrically (nearest hazard carry, green center vs pin) instead of trusting the user.

Manual correction UI: course viewer in Streamlit renders the hole polygon via `pydeck`; user can drag the pin marker and "save correction" back into the course JSON.

Acceptance criteria

- An Overpass fetch for a known public course (e.g., Bethpage Black osm relation id) parses into a `Course` with 18 holes and ≥1 hazard per hole on average.
- `Pipeline.run()` given (`course_id`, `hole=7`, `tee_lat_lon=...`) returns the same distance as `ContextAgent` with manual `distance_to_target` within ±3 yards.
- Tests use cached Overpass fixtures; no live network in CI.

### Phase 4 — Pin & Target Data

Goal: upgrade pin position from a 3-value enum to real coordinates where available, with clean fallback.

Tiered sources

- Manual daily entry (v1): admin form, three taps on the green polygon (`front/middle/back`) or single tap → saved to `data/pins/<course_id>/<YYYY-MM-DD>.json`.
- GolfPin commercial feed (v2, optional): `utils/data_sources/golfpin.py` behind an API key. Only triggered if `GOLFPIN_API_KEY` env var is set.
- User snapshot: the Streamlit UI offers "tap pin on green" during a round, caching that pin for the rest of the session.

Model addition: `ShotContext.pin_lat_lon: LatLon | None`. The existing `pin_position` enum is derived from `pin_lat_lon + green polygon` when coords are present.

Agent integration: `DecisionAgent.actual_distance` uses `pin_lat_lon` when available; falls back to `distance_to_target` otherwise.

Acceptance criteria

- Tapping a pin on a course's green polygon stores a file and is reloaded for the same date.
- With a known pin position, `plays_like_distance` changes measurably vs `front/middle/back` enum for a back-pin hole.

### Phase 5 — Real Evaluation Dataset & Feedback Loop

Goal: stop evaluating only on hand-written benchmarks. Log every real recommendation + outcome and use them to score the system.

New module: `utils/evaluation/recorder.py`.

Logged record schema (`data/evaluation/runs.jsonl`, append-only):

```python
class RunRecord(BaseModel, frozen=True):
    run_id: str
    timestamp: datetime
    raw_input: dict
    shot_context: ShotContext
    decision: CaddyDecision
    adaptive_decision: AdaptiveDecision | None
    explanation_summary: str
    player_id: str | None
    outcome: ShotFeedback | None      # filled in later from the feedback form
    latency_ms: dict[str, float]      # mirrors Pipeline timing
```

Evaluation job: `scripts/evaluate_runs.py` joins `runs.jsonl` with `ShotFeedback`, computes:

- Primary-club agreement with the club actually used.
- Directional hit rate (did the miss direction match the predicted confidence tier?).
- Confidence calibration (Brier score of high/medium/low vs. `good_contact/short/long/thin/fat`).

Benchmark promotion: any recorded run with outcome + explicit "good call / bad call" flag is eligible for promotion into `benchmarks/real_shots.json`, reviewed in a small admin screen.

Acceptance criteria

- Every call to `Pipeline.run()` appends exactly one `RunRecord`.
- `scripts/evaluate_runs.py` produces a markdown report with calibration + agreement metrics.
- At least 50 real records drive a baseline number before any further prompt tuning.

## 5. Cross-Cutting Concerns

Rate limits & licensing

- Nominatim: 1 request/second, attribute OSM, no bulk geocoding — use the cache aggressively.
- Open-Meteo: free for non-commercial; include attribution in footer.
- OSM/Overpass: ODbL attribution required; do not redistribute derived tiles.
- USGS EPQS: public domain.
- Do not use Google Maps for geocoding, tiles, or elevation in v1.
- Secrets: all keys in `.env` only, never committed. Loader in `utils/config.py`.

Failure modes: every `data_sources/*` call must be wrapped so that a `5xx`/timeouts degrades cleanly to the existing manual input path. Pipeline should never raise from a data-source outage.

Observability: `PipelineLogger` gains a `data_source` step type so dashboards can see cache hit rate and per-source latency.

Testing: network-touching code goes under `tests/data_sources/` and `tests/importers/` with VCR/Cassette fixtures; no live HTTP in CI. The existing 92 tests must remain green throughout.

## 6. Recommended Execution Order (V1 Stack, ~5–7 weeks solo)

| Week | Deliverable |
|---|---|
| 1 | Phase 1 weather + elevation connectors + cache + UI hookup |
| 2 | Phase 2 TrackMan importer + profile rebuild + tests |
| 3 | Phase 2 Foresight/Golf Pad + tendency rebuild |
| 4 | Phase 3 Overpass ingest + Course model + one seed course |
| 5 | Phase 3 pipeline integration + pin manual UI (Phase 4 tier 1) |
| 6 | Phase 5 run recorder + `evaluate_runs.py` + first 50 real runs |
| 7 | Polish, documentation, optional GolfPin tier |

## 7. Paid Upgrade Path (optional, post-v1)

| Need | Paid option | Trigger to adopt |
|---|---|---|
| Tour-grade course catalog | USGA API, GolfCourseAPI, SportsFirst | Need for course ratings / slope |
| Official daily pin sheets | GolfPin subscription | Users request tournament-day accuracy |
| High-res elevation for slope | USGS 3DEP LiDAR tiles | OSM+EPQS insufficient for green reads |
| Tour shot datasets for calibration | PGA ShotLink (licensed) | Model tuning saturates on personal data |

## 8. Success Definition

The project exits v1 when, on a laptop with no manual input beyond "course + hole + my uploaded bag," the pipeline produces a club recommendation whose primary-club agreement with the shot the player actually chooses is ≥70% across a rolling 100-shot window, with calibrated confidence (Brier ≤ 0.2). Everything in this plan exists to make that measurable.
