# Agentic Golf Caddy

A bounded multi-agent golf caddie built in Python and Streamlit.

Repository: `https://github.com/AlexCannonUSF/agentic-golf-caddy`

The project keeps the club-distance math deterministic for reliability, then adds AI around that core for:
- free-text shot parsing
- selective clarification
- bounded strategy adaptation
- grounded explanation
- post-shot learning from feedback

## What makes it agentic

The app runs a hybrid pipeline instead of a single black-box prompt:

1. `Input Interpreter Agent`
   - parses free-text golf language into structured shot data
2. `Clarification Agent`
   - asks for one follow-up only when uncertainty is likely to change the result
3. `Context Agent`
   - normalizes the shot and optionally enriches it with course, weather, elevation, and pin data
4. `Decision Agent`
   - computes plays-like distance and produces deterministic club candidates
5. `Adaptive Strategy Agent`
   - re-ranks only the bounded candidate list using lie, hazards, player confidence, and shot history
6. `Coach Agent`
   - explains the recommendation in golfer-friendly language
7. `Verifier Agent`
   - checks that the final explanation stays grounded in the real decision data

## Current capabilities

### Core golf engine
- Plays-like distance calculation with wind, elevation, lie, temperature, and altitude adjustments
- Deterministic club selection with strategy bias and lie-aware guardrails
- Confidence scoring
- Primary and backup club recommendations

### Agentic behavior
- Free-text shot interpretation
- Selective clarification for ambiguous input
- Adaptive shortlist re-ranking
- Forced layup behavior when the carry is not realistic from a bad lie
- Grounded explanation fallback when an LLM output is unsafe or unsupported

### Real-data features
- Live weather from Open-Meteo
- Elevation from USGS EPQS
- Geocoding through Nominatim
- Saved real-course geometry from OpenStreetMap / Overpass
- Daily pin storage and pin-coordinate targeting
- Real-run logging and evaluation

### Player modeling
- Four default skill-level profiles
- Public benchmark profiles across handicap buckets plus PGA / LPGA reference profiles
- TrackMan, Foresight FSX, and Golf Pad CSV import
- Local shot-history storage and tendency rebuilding

## Quick start

### Requirements
- Python 3.11+
- Git
- Optional: `OPENAI_API_KEY` for LLM-powered interpretation, strategy notes, and coaching copy. Without it, the app still runs with deterministic fallbacks.

### Run from GitHub

Copy and paste these commands into your terminal:

```bash
git clone https://github.com/AlexCannonUSF/agentic-golf-caddy.git
cd agentic-golf-caddy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

If you want the optional LLM features, edit `.env` and set `OPENAI_API_KEY`.

### Run in the terminal

After installing the requirements, make sure the virtual environment is active:

```bash
source .venv/bin/activate
```

Then start the Streamlit UI:

```bash
python main.py
```

The app will print a local URL, usually `http://localhost:8501`.

You can also run the shell wrapper:

```bash
./run_app.sh
```

Or launch Streamlit directly:

```bash
streamlit run app.py
```

### Terminal command checklist

For a fresh checkout, this is the full terminal flow:

```bash
git clone https://github.com/AlexCannonUSF/agentic-golf-caddy.git
cd agentic-golf-caddy
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

### Verify the project

```bash
pytest
```

Run the synthetic multi-agent evaluation:

```bash
python -m evaluation --profile intermediate
```

### IDE run option

#### PyCharm / IntelliJ easiest path
1. Open `main.py`.
2. Click the green Run button.
3. The wrapper launches Streamlit automatically.

`main.py` and `run_app.sh` were set up so the app still launches cleanly when the IDE Python SDK is flaky, as long as the project `.venv` exists.

## Fastest demo flow for grading

If you need a clean submission demo, this is the fastest path:

1. Run the app.
2. Choose a benchmark profile such as `Shot Scope Benchmark 10 Handicap`.
3. Optionally select `Torrey Pines South Course` in the sidebar.
4. Enter a shot either:
   - in structured form, or
   - in free text like `145 out, into the wind, back pin, I just want middle of the green`.
5. Show the output sections:
   - parsed shot intent
   - final club recommendation
   - adaptive caddie note
   - confidence
   - plays-like distance
   - backup club
6. Submit shot feedback to show how the system learns tendencies over time.

Good demo scenarios:
- standard fairway approach
- bunker approach where the app protects against bad woods/hybrids
- deep-rough long shot where the app explicitly switches to a layup strategy
- free-text shot with target preference like `middle of the green`

Example free-text prompts to try in the app:
- `145 out, into the wind, back pin, I just want middle of the green`
- `185 yards from deep rough with water short, play it safe`
- `92 yards from a bunker, front pin, low confidence`
- `210 to the green, downhill, trouble long, aggressive line`

## How to use the main features

### 1. Use structured input
- Enter distance, lie, wind, elevation, temperature, strategy, and target mode.
- Submit the shot.
- Review the recommendation context, club banner, adaptive note, and backup club.

### 2. Use free-text input
- Open the free-text tab.
- Describe the shot naturally.
- The interpreter extracts distance, lie, hazards, target mode, and user intent.
- If the input is too ambiguous, the clarification agent pauses for one meaningful follow-up.

### 3. Import your own shot data
1. Open `Upload My Shots` in the sidebar.
2. Upload a CSV from TrackMan, Foresight FSX, or Golf Pad.
3. Review the detected source and rebuilt club distances.
4. Save the imported profile.
5. Switch to that profile and run recommendations normally.

Notes:
- Imported histories are stored under `data/players/<player_id>/`.
- The app uses `shots.parquet` when `pyarrow` is available, otherwise it falls back to `shots.jsonl`.

### 4. Use a saved course
1. Select a saved course in the sidebar.
2. Choose a hole and tee.
3. Review the hole preview.
4. Run a recommendation.

Notes:
- If you already know the shot distance, that explicit distance stays in control.
- Course geometry fills in context, not the other way around.
- Long-hole geometry can still inform layup targets when the shot itself is not explicitly known.

### 5. Use daily pin data
1. Select a course, hole, and tee.
2. Open `Pin Setup`.
3. Pick a date and a pin source.
4. Save the current pin if needed.
5. Run the shot again to use the active pin coordinate.

### 6. Evaluate real runs
Each finished recommendation is logged to `data/evaluation/runs.jsonl`.

Generate a real-run report:

```bash
python scripts/evaluate_runs.py --output data/evaluation/real_run_report.md
```

Export promotable benchmark cases:

```bash
python scripts/evaluate_runs.py --export-benchmarks
```

Run the synthetic benchmark suite:

```bash
python -m evaluation --profile intermediate
```

## Included data and profiles

### Benchmarks
- `benchmarks/deterministic_scenarios.json`
- `benchmarks/adaptive_scenarios.json`
- `benchmarks/clarification_scenarios.json`

### Built-in benchmark profiles
- Shot Scope Benchmark 0 / 5 / 10 / 15 / 20 / 25 Handicap
- TrackMan PGA Tour Average 2024
- TrackMan LPGA Tour Average 2024

Source notes live in `docs/BENCHMARK_PROFILES.md`.

## Project structure

- `agents/` multi-agent pipeline logic
- `engine/` deterministic golf heuristics
- `models/` typed Pydantic contracts
- `ui/` Streamlit presentation components
- `utils/` persistence, imports, data sources, and helpers
- `evaluation/` benchmark and run-evaluation tooling
- `benchmarks/` starter scenario datasets
- `profiles/` built-in and saved player profiles
- `prompts/` prompt templates used by optional LLM-backed agents
- `scripts/` command-line utilities for evaluation reports
- `tests/` regression and integration tests
- `docs/` source notes and project documentation
- `data/` local cache, feedback, runs, players, pins, and courses

Generated local files are intentionally ignored:
- `data/cache/`
- `data/evaluation/`
- `data/players/`
- `data/pins/`
- `profiles/imported_*.json`
- local virtual environments, IDE files, Python caches, logs, and Office lock files

## Submission notes

What this project does well:
- Keeps golf math deterministic and testable
- Uses multiple agents for ambiguity handling, adaptation, and verification
- Supports both synthetic evaluation and real-run logging
- Demonstrates real-data integration without depending on paid APIs

Current boundaries:
- The benchmark suite is most directly calibrated to the matching profile assumptions rather than every profile equally.
- The app now explicitly lays up in clearly unrealistic bad-lie carry situations, but it is still a caddie assistant, not a launch-monitor-grade simulator.
- LLM behavior is bounded by deterministic candidate clubs and grounded explanation checks.

## Solo contribution

This was completed as a solo project by Alex Cannon. Alex was responsible for the project idea, system design, Streamlit user interface, agent orchestration, deterministic golf engine, data importers, evaluation harness, tests, and documentation.

## Code and source attribution

Project code was developed for this class project by Alex Cannon. Claude and OpenAI ChatGPT/Codex were used as coding assistants for implementation support, refactoring, review, comments, and documentation. Alex reviewed, tested, and accepted the final code. No third-party source code was copied into this repository.

External data and service sources used by the application or benchmark profiles:
- Open-Meteo Forecast API for live weather lookups.
- USGS EPQS for elevation lookups.
- Nominatim and OpenStreetMap / Overpass for geocoding and public course geometry.
- Shot Scope handicap-distance data, entered from the public Golf Monthly article documented in `docs/BENCHMARK_PROFILES.md`.
- TrackMan 2024 tour-average distance data, entered from public TrackMan/Golf Monthly tables documented in `docs/BENCHMARK_PROFILES.md`.

Secrets and private user data are not committed. API keys belong in `.env`, and imported player histories or run logs are stored under ignored `data/` paths.

## Related docs

- `docs/BENCHMARK_PROFILES.md`
