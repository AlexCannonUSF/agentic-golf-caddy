"""Typed output contract for the decision agent."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.enums import ConfidenceLevel


class CaddyDecision(BaseModel):
    """Final deterministic recommendation payload before explanation."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    primary_club: str = Field(..., min_length=1)
    backup_club: str = Field(..., min_length=1)
    plays_like_distance: float = Field(..., ge=0.0, le=500.0)
    actual_distance: float = Field(..., ge=0.0, le=500.0)
    adjustments: dict[str, float] = Field(default_factory=dict)
    confidence: ConfidenceLevel
    strategy_note: str = Field(..., min_length=1)

    @field_validator("plays_like_distance", "actual_distance", mode="before")
    @classmethod
    def _coerce_numeric(cls, value: Any) -> float:
        if isinstance(value, bool):
            raise ValueError("Boolean values are not valid numeric inputs.")
        try:
            return round(float(value), 1)
        except (TypeError, ValueError) as exc:
            raise ValueError("Value must be numeric.") from exc

    @field_validator("adjustments", mode="before")
    @classmethod
    def _coerce_adjustments(cls, value: Any) -> dict[str, float]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise TypeError("adjustments must be a mapping of adjustment_name -> yards.")

        normalized: dict[str, float] = {}
        for key, raw_amount in value.items():
            name = str(key).strip()
            if not name:
                raise ValueError("Adjustment names cannot be blank.")
            try:
                normalized[name] = round(float(raw_amount), 1)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Adjustment '{name}' must be numeric.") from exc
        return normalized

    @model_validator(mode="after")
    def _validate_relationships(self) -> "CaddyDecision":
        if self.primary_club.lower() == self.backup_club.lower():
            raise ValueError("Primary and backup clubs must be different.")

        calculated_plays_like = round(self.actual_distance + sum(self.adjustments.values()), 1)
        if abs(calculated_plays_like - self.plays_like_distance) > 1.0:
            raise ValueError(
                "plays_like_distance must approximately equal actual_distance + sum(adjustments)."
            )
        return self
