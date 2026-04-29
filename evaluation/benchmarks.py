# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Load benchmark scenarios from checked-in JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evaluation.models import ClarificationBenchmarkCase, ScenarioBenchmarkCase
from models import PlayerTendencies, ShotFeedback

_BENCHMARKS_DIR = Path(__file__).resolve().parents[1] / "benchmarks"


def _load_json(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and isinstance(payload.get("cases"), list):
        payload = payload["cases"]
    if not isinstance(payload, list):
        raise ValueError(f"Benchmark file must contain a list of cases: {path}")
    return [
        item
        for item in payload
        if isinstance(item, dict) and "_ai_disclosure" not in item
    ]


def _load_tendencies(raw_value: Any) -> PlayerTendencies | None:
    if raw_value in (None, {}):
        return None
    return PlayerTendencies.model_validate(raw_value)


def _load_feedback(raw_items: Any) -> tuple[ShotFeedback, ...]:
    if not raw_items:
        return ()
    return tuple(ShotFeedback.model_validate(item) for item in raw_items)


def load_scenario_cases(filename: str) -> list[ScenarioBenchmarkCase]:
    """Load deterministic or adaptive structured scenario cases."""

    path = _BENCHMARKS_DIR / filename
    cases: list[ScenarioBenchmarkCase] = []
    for item in _load_json(path):
        expected_club = str(item["expected_club"])
        acceptable = tuple(item.get("acceptable_clubs") or [expected_club])
        cases.append(
            ScenarioBenchmarkCase(
                case_id=str(item["case_id"]),
                raw_input=dict(item["raw_input"]),
                expected_club=expected_club,
                acceptable_clubs=acceptable,
                expected_plays_like_distance=item.get("expected_plays_like_distance"),
                feedback_history=_load_feedback(item.get("feedback_history")),
                profile_tendencies=_load_tendencies(item.get("profile_tendencies")),
                tags=tuple(item.get("tags", [])),
            )
        )
    return cases


def load_clarification_cases(filename: str = "clarification_scenarios.json") -> list[ClarificationBenchmarkCase]:
    """Load natural-language clarification benchmark cases."""

    path = _BENCHMARKS_DIR / filename
    cases: list[ClarificationBenchmarkCase] = []
    for item in _load_json(path):
        expected_final = item.get("expected_final_club")
        acceptable = tuple(item.get("acceptable_final_clubs") or ([expected_final] if expected_final else []))
        cases.append(
            ClarificationBenchmarkCase(
                case_id=str(item["case_id"]),
                shot_text=str(item["shot_text"]),
                expected_needs_clarification=bool(item["expected_needs_clarification"]),
                clarified_input=dict(item.get("clarified_input", {})),
                expected_final_club=str(expected_final) if expected_final else None,
                acceptable_final_clubs=acceptable,
                expected_question_contains=item.get("expected_question_contains"),
                feedback_history=_load_feedback(item.get("feedback_history")),
                profile_tendencies=_load_tendencies(item.get("profile_tendencies")),
                tags=tuple(item.get("tags", [])),
            )
        )
    return cases


def load_deterministic_cases() -> list[ScenarioBenchmarkCase]:
    """Load the starter deterministic benchmark."""

    return load_scenario_cases("deterministic_scenarios.json")


def load_adaptive_cases() -> list[ScenarioBenchmarkCase]:
    """Load the starter adaptive benchmark."""

    return load_scenario_cases("adaptive_scenarios.json")
