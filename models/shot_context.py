# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Typed shot input context shared between agents."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.environment import LatLon
from models.enums import Elevation, LieType, PinPosition, Strategy, TargetMode, WindDirection


class ShotContext(BaseModel):
    """Validated shot context produced by the input/context agent."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    distance_to_target: float = Field(
        ...,
        ge=30.0,
        le=350.0,
        description="Actual distance to target in yards.",
    )
    lie_type: LieType = Field(default=LieType.FAIRWAY)
    wind_speed: float = Field(default=0.0, ge=0.0, le=40.0)
    wind_direction: WindDirection = Field(default=WindDirection.HEADWIND)
    elevation: Elevation = Field(default=Elevation.FLAT)
    strategy: Strategy = Field(default=Strategy.NEUTRAL)
    temperature: float = Field(default=72.0, ge=20.0, le=120.0)
    altitude_ft: float = Field(default=0.0, ge=0.0, le=10000.0)
    target_mode: TargetMode = Field(default=TargetMode.PIN)
    pin_position: PinPosition | None = Field(default=None)
    origin_lat_lon: LatLon | None = Field(default=None)
    pin_lat_lon: LatLon | None = Field(default=None)
    hazard_note: str | None = Field(default=None, max_length=120)
    player_confidence: int | None = Field(default=None, ge=1, le=5)

    @field_validator("distance_to_target", "wind_speed", "temperature", "altitude_ft", mode="before")
    @classmethod
    def _coerce_numeric(cls, value: Any) -> float:
        if isinstance(value, bool):
            raise ValueError("Boolean values are not valid numeric inputs.")
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Value must be numeric.") from exc

    @field_validator("distance_to_target", "wind_speed", "temperature", "altitude_ft")
    @classmethod
    def _round_numeric(cls, value: float) -> float:
        return round(value, 1)

    @field_validator("hazard_note", mode="before")
    @classmethod
    def _blank_hazard_to_none(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("player_confidence", mode="before")
    @classmethod
    def _coerce_confidence(cls, value: Any) -> int | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            raise ValueError("player_confidence must be numeric.")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("player_confidence must be numeric.") from exc
