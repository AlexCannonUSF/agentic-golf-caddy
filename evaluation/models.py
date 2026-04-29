# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Typed benchmark and evaluation records."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from models import PlayerTendencies, ShotFeedback


class EvaluationVariant(str, Enum):
    """Supported evaluation pipeline variants."""

    DETERMINISTIC_ONLY = "deterministic_only"
    DETERMINISTIC_PLUS_EXPLANATION = "deterministic_plus_explanation"
    BOUNDED_HYBRID = "bounded_hybrid"


@dataclass(frozen=True)
class ScenarioBenchmarkCase:
    """Structured scenario used for deterministic or adaptive evaluation."""

    case_id: str
    raw_input: dict[str, Any]
    expected_club: str
    acceptable_clubs: tuple[str, ...]
    expected_plays_like_distance: float | None = None
    feedback_history: tuple[ShotFeedback, ...] = ()
    profile_tendencies: PlayerTendencies | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClarificationBenchmarkCase:
    """Natural-language scenario used to evaluate clarification behavior."""

    case_id: str
    shot_text: str
    expected_needs_clarification: bool
    clarified_input: dict[str, Any] = field(default_factory=dict)
    expected_final_club: str | None = None
    acceptable_final_clubs: tuple[str, ...] = ()
    expected_question_contains: str | None = None
    feedback_history: tuple[ShotFeedback, ...] = ()
    profile_tendencies: PlayerTendencies | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScenarioOutcome:
    """Prediction produced for a structured benchmark case."""

    case_id: str
    variant: EvaluationVariant
    primary_club: str | None
    backup_club: str | None
    plays_like_distance: float | None
    explanation_grounded: bool | None = None
    corrected_output_used: bool = False
    produced_valid_result: bool = False


@dataclass(frozen=True)
class ClarificationOutcome:
    """Prediction produced for a clarification benchmark case."""

    case_id: str
    asked_clarification: bool
    question: str | None
    guessed_without_clarification: str | None
    clarified_club: str | None
    final_club: str | None
    produced_valid_result: bool

