# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Persistent run-record model for real recommendation evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.agentic import AdaptiveDecision, ClarificationResult, ShotFeedback, ShotIntent, VerificationResult
from models.caddy_decision import CaddyDecision
from models.explanation import Explanation
from models.shot_context import ShotContext


class RunRecord(BaseModel):
    """One logged pipeline execution used for real-world evaluation."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    run_id: str = Field(..., min_length=1)
    timestamp: datetime
    status: Literal["completed", "clarification_required"] = "completed"
    raw_input: dict[str, Any] = Field(default_factory=dict)
    shot_intent: ShotIntent | None = None
    clarification: ClarificationResult | None = None
    shot_context: ShotContext | None = None
    decision: CaddyDecision | None = None
    adaptive_decision: AdaptiveDecision | None = None
    explanation: Explanation | None = None
    explanation_summary: str | None = None
    verification: VerificationResult | None = None
    player_id: str | None = None
    profile_name: str | None = None
    outcome: ShotFeedback | None = None
    latency_ms: dict[str, float] = Field(default_factory=dict)

    @field_validator("timestamp", mode="before")
    @classmethod
    def _normalize_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            timestamp = value
        else:
            timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc)

    @field_validator("explanation_summary", "player_id", "profile_name", mode="before")
    @classmethod
    def _blank_text_to_none(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("latency_ms")
    @classmethod
    def _round_latencies(cls, value: dict[str, float]) -> dict[str, float]:
        return {key: round(float(latency), 1) for key, latency in value.items()}
