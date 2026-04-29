<!-- AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts. -->

# Codebase Walkthrough

This document explains the code in plain English. The goal is to make it easy for a grader or future developer to understand how the project is organized, how the agents work together, and where each feature lives.

## Big Picture

Agentic Golf Caddy is a Streamlit application that recommends a golf club for a shot. It combines deterministic golf calculations with a multi-agent pipeline:

1. The user enters a shot in the UI.
2. The input interpreter turns free text or form fields into structured shot data.
3. The clarification agent asks one follow-up question only when an important detail is missing or uncertain.
4. The context agent validates the shot and can enrich it with course, pin, weather, and elevation data.
5. The decision agent calculates plays-like distance and picks deterministic club candidates.
6. The adaptive strategy agent re-ranks only that bounded candidate list using hazards, lie, confidence, and player history.
7. The coach agent explains the recommendation in simple golfer language.
8. The verifier agent checks that the explanation does not invent unsupported clubs or numbers.
9. The run recorder logs the result for later evaluation.

The important design choice is that the golf math stays deterministic and testable. Optional LLM calls are used around that core, but the app still works without an API key.

## How To Run It

The main terminal flow is:

```bash
git clone https://github.com/AlexCannonUSF/agentic-golf-caddy.git
cd agentic-golf-caddy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

`main.py` starts the Streamlit app in `app.py`. The app prints a local URL such as `http://localhost:8501`.

## Main Entry Points

- `main.py`
  - Small launcher for terminal or IDE use.
  - Re-runs itself with the project `.venv` interpreter when that exists.
  - Starts Streamlit with `app.py`.

- `app.py`
  - Main Streamlit UI.
  - Builds the sidebar, profile selector, course selector, pin setup, shot input form, recommendation output, feedback form, and evaluation panels.
  - Uses `st.session_state` to keep choices and the latest recommendation across Streamlit reruns.
  - Calls `Pipeline.run(...)` when the user submits a shot.

- `run_app.sh`
  - Shell wrapper for starting the app with `.venv/bin/python`.

## Agent Files

The `agents/` folder contains the multi-agent system.

- `agents/pipeline.py`
  - Orchestrates the full workflow.
  - Creates one `PipelineResult` containing shot intent, clarification state, context, deterministic decision, adaptive decision, explanation, verification, and timing.
  - Records each run through `RunRecorder`.

- `agents/input_interpreter_agent.py`
  - Handles both structured input and free-text descriptions.
  - If `OPENAI_API_KEY` is set, it can ask an LLM to parse the shot.
  - If no key is set, it uses a heuristic parser that recognizes common golf phrases such as "145 out", "into the wind", "deep rough", and "middle of the green".

- `agents/clarification_agent.py`
  - Decides whether the app needs to pause and ask one follow-up.
  - Example: if distance is missing, it asks for yardage before recommending a club.
  - It avoids unnecessary questions when the input is already good enough.

- `agents/context_agent.py`
  - Validates raw input into a `ShotContext`.
  - Adds optional real-world context from saved courses, saved pins, weather, and elevation.
  - Keeps explicit user-entered distance in control when the user provides one.

- `agents/decision_agent.py`
  - Computes plays-like distance.
  - Calls the club selector to choose the deterministic primary and backup clubs.
  - Assigns a confidence level.

- `agents/adaptive_strategy_agent.py`
  - Looks only at the deterministic shortlist of candidate clubs.
  - Can use an LLM when configured, but also has a deterministic fallback strategy.
  - Applies guardrails for bunker and deep rough situations, including forced layups when full carry is unrealistic.

- `agents/coach_agent.py`
  - Produces the user-facing explanation.
  - Uses an LLM only when `OPENAI_API_KEY` exists.
  - Uses a deterministic template fallback when no key is set or the LLM fails.

- `agents/verifier_agent.py`
  - Checks the explanation for unsupported clubs or numbers.
  - If the explanation is not grounded, the pipeline replaces it with the deterministic template.

## Engine Files

The `engine/` folder holds deterministic golf logic.

- `engine/distance_engine.py`
  - Aggregates all distance adjustments.
  - Converts raw distance into plays-like distance.
  - Uses exact pin coordinates when available and when the target mode is `pin`.

- `engine/wind.py`
  - Converts wind speed and direction into yardage adjustment.

- `engine/elevation.py`
  - Converts elevation buckets such as uphill or downhill into yardage adjustment.

- `engine/lie.py`
  - Converts lie type such as fairway, rough, deep rough, or bunker into yardage adjustment.

- `engine/environment.py`
  - Handles temperature and altitude adjustments.

- `engine/club_selector.py`
  - Ranks clubs by distance fit plus penalties for strategy, lie, hazards, and player tendencies.
  - Chooses a primary club and a backup club.
  - Returns a bounded candidate list for the adaptive strategy agent.

- `engine/confidence.py`
  - Scores confidence based on club-distance fit.
  - Lowers confidence for difficult conditions such as extreme wind, bad lies, steep elevation, or low player confidence.

## Model Files

The `models/` folder defines typed Pydantic data contracts used across the app.

- `models/enums.py`
  - Shared enum values such as lie type, wind direction, strategy, target mode, and shot outcome.

- `models/shot_context.py`
  - Clean validated shot context used by the engine and agents.

- `models/player_profile.py`
  - Player profile with club distances, skill level, preferred shot, and tendencies.

- `models/caddy_decision.py`
  - Final deterministic club decision fields.

- `models/agentic.py`
  - Agent-specific models such as `ShotIntent`, `ClarificationResult`, `AdaptiveDecision`, and `VerificationResult`.

- `models/explanation.py`
  - Structured explanation shown to the user.

- `models/course.py`
  - Saved course geometry including holes, tees, greens, fairways, and hazards.

- `models/environment.py`
  - Weather and latitude/longitude models.

- `models/pins.py`
  - Daily pin sheet and hole pin models.

- `models/shot_event.py`
  - Normalized imported shot data from TrackMan, Foresight, or Golf Pad.

- `models/run_record.py`
  - Logged recommendation run used for later evaluation.

## UI Files

The `ui/` folder keeps display helpers separate from the main app file.

- `ui/components.py`
  - Reusable Streamlit display sections such as the hero, club banner, confidence badge, explanation cards, and debug panels.

- `ui/styles.py`
  - CSS used to make the Streamlit app more polished and readable.

- `ui/scenarios.py`
  - Preloaded demo scenarios for quickly filling the input form.

## Utility Files

The `utils/` folder contains persistence, validation, importers, data-source connectors, and helper logic.

- `utils/validators.py`
  - Normalizes and validates raw shot input.
  - Accepts friendly aliases like `sand` for bunker or `attack` for aggressive.

- `utils/profile_manager.py`
  - Loads and saves player profile JSON files under `profiles/`.

- `utils/feedback_manager.py`
  - Stores user feedback and turns it into lightweight player tendencies.

- `utils/course_manager.py`
  - Loads and saves course JSON files under `data/courses/`.

- `utils/pin_manager.py`
  - Loads and saves daily pin positions under `data/pins/`.

- `utils/geometry.py`
  - Distance, centroid, projection, and polygon helpers used by course and pin logic.

- `utils/config.py`
  - Central configuration helpers for paths, HTTP timeout, and `.env` loading.

- `utils/logger.py`
  - Pipeline logging helpers.

- `utils/wizard.py`
  - Builds a player profile from quick calibration values.

## Data Source Files

The `utils/data_sources/` folder talks to public data sources and caches results.

- `cache.py`
  - Disk-backed JSON cache so repeated API calls are fast and reproducible.

- `weather.py`
  - Fetches weather from Open-Meteo.

- `elevation.py`
  - Fetches elevation from USGS EPQS.

- `geocode.py`
  - Geocodes course/location names through Nominatim.
  - Throttles requests to respect Nominatim usage expectations.

- `overpass.py`
  - Fetches golf course geometry from OpenStreetMap/Overpass.

- `osm_parser.py`
  - Converts Overpass payloads into the internal `Course` model.

## Importer Files

The `utils/importers/` folder normalizes shot-history CSV files.

- `_helpers.py`
  - Shared CSV parsing, header normalization, timestamp parsing, and player id helpers.

- `trackman.py`
  - Imports TrackMan CSV rows into `ShotEvent` models.

- `foresight.py`
  - Imports Foresight FSX CSV rows into `ShotEvent` models.

- `golfpad.py`
  - Imports Golf Pad CSV rows into `ShotEvent` models.

- `normalizer.py`
  - Builds a `PlayerProfile` and `PlayerTendencies` from imported shots.
  - Saves shots as Parquet when available, otherwise JSONL.

## Evaluation Files

The `evaluation/` folder is used to measure functionality and reliability.

- `evaluation/runner.py`
  - Runs deterministic, explanation, adaptive, clarification, and failure-recovery benchmark variants.

- `evaluation/benchmarks.py`
  - Loads benchmark JSON files from `benchmarks/`.

- `evaluation/metrics.py`
  - Calculates accuracy, validity, grounding, clarification, and fallback metrics.

- `evaluation/models.py`
  - Dataclasses used by the benchmark runner.

- `evaluation/real_runs.py`
  - Summarizes real recorded user runs.

- `scripts/evaluate_runs.py`
  - Command-line script for generating real-run evaluation reports.

## Data And Prompt Files

- `benchmarks/`
  - JSON scenarios used by the evaluation runner.

- `profiles/`
  - Default player profiles and public benchmark distance profiles.

- `data/courses/`
  - Checked-in example course files.

- `prompts/`
  - Prompt templates for optional LLM-backed agents.

- `docs/BENCHMARK_PROFILES.md`
  - Source notes for public benchmark profile data.

## Tests

The `tests/` folder covers the important system behavior:

- engine math
- model validation
- agent behavior
- pipeline integration
- course and pin management
- public data-source parsing with fixtures
- shot importers
- evaluation reporting

Run all tests with:

```bash
pytest
```

## Generated Files

The app can generate local files while running:

- `data/cache/` for API cache files
- `data/evaluation/` for run logs
- `data/players/` for imported shot histories
- `data/pins/` for saved daily pins
- `profiles/imported_*.json` for imported player profiles

These are ignored by Git so private user data and runtime output are not committed.

## Why This Satisfies The Project

- It has a functional user interface through Streamlit.
- It uses multiple cooperating agents rather than one prompt.
- It includes deterministic golf logic, optional LLM support, data enrichment, feedback, and evaluation.
- It has tests and benchmark evaluation.
- It documents how to run the app, how the code is organized, and what sources were used.
