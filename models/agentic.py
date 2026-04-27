"""Additional models supporting the agentic workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.enums import PinPosition, PreferredShot, RecommendationRating, ShotOutcome, TargetMode


class CourseContext(BaseModel):
    """Extra shot context used by adaptive and planning agents."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    target_mode: TargetMode = Field(default=TargetMode.PIN)
    pin_position: PinPosition | None = Field(default=None)
    hazard_note: str | None = Field(default=None, max_length=120)

    @field_validator("hazard_note", mode="before")
    @classmethod
    def _blank_hazard_to_none(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class UserIntent(BaseModel):
    """User goal extracted from natural-language shot descriptions."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    goal: str | None = Field(default=None, max_length=60)

    @field_validator("goal", mode="before")
    @classmethod
    def _blank_goal_to_none(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class ShotIntent(BaseModel):
    """Structured result of parsing a natural-language shot description."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    raw_text: str = Field(..., min_length=1)
    parsed_fields: dict[str, str | float | int | None] = Field(default_factory=dict)
    field_confidence: dict[str, float] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    ambiguous_fields: list[str] = Field(default_factory=list)
    course_context: CourseContext = Field(default_factory=CourseContext)
    user_intent: UserIntent = Field(default_factory=UserIntent)
    user_facing_summary: str = Field(default="")


class ClarificationResult(BaseModel):
    """Whether the system should pause and ask a follow-up question."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    needs_clarification: bool
    question: str | None = Field(default=None)
    reason: str = Field(default="")
    decision_sensitivity: float = Field(default=0.0, ge=0.0, le=1.0)


class CandidateOption(BaseModel):
    """A deterministic candidate club the adaptive layer is allowed to choose."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    club_name: str = Field(..., min_length=1)
    club_distance: float = Field(..., gt=0.0)
    distance_gap: float = Field(..., ge=0.0)


class PlayerTendencies(BaseModel):
    """Player tendencies derived from profile and shot history."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    common_miss: str | None = Field(default=None, max_length=60)
    shot_shape: PreferredShot | None = Field(default=None)
    confidence_by_club: dict[str, float] = Field(default_factory=dict)
    dispersion_by_club: dict[str, float] = Field(default_factory=dict)

    @field_validator("common_miss", mode="before")
    @classmethod
    def _blank_common_miss_to_none(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class AdaptiveDecision(BaseModel):
    """Bounded recommendation chosen from deterministic candidate clubs."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    recommended_club: str = Field(..., min_length=1)
    target_line: str = Field(default="pin", min_length=1)
    strategy_rationale: str = Field(..., min_length=1)
    risk_flags: list[str] = Field(default_factory=list)
    used_history: bool = Field(default=False)


class VerificationResult(BaseModel):
    """Result of grounding checks on the final explanation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    is_grounded: bool
    issues: list[str] = Field(default_factory=list)
    corrected_output_used: bool = Field(default=False)


class ShotFeedback(BaseModel):
    """Stored feedback describing how a recommended shot actually turned out."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    run_id: str | None = Field(default=None, min_length=1)
    club_used: str = Field(..., min_length=1)
    outcome: ShotOutcome
    recommendation_rating: RecommendationRating | None = Field(default=None)
    actual_outcome_note: str | None = Field(default=None, max_length=160)
    captured_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("run_id", mode="before")
    @classmethod
    def _blank_run_id_to_none(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("actual_outcome_note", mode="before")
    @classmethod
    def _blank_note_to_none(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("captured_at", mode="before")
    @classmethod
    def _normalize_captured_at(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            captured_at = value
        else:
            captured_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if captured_at.tzinfo is None:
            return captured_at.replace(tzinfo=timezone.utc)
        return captured_at.astimezone(timezone.utc)
