"""Normalized shot-history event model used for real profile imports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.enums import LieType
from models.player_profile import canonicalize_club_name


class ShotEvent(BaseModel):
    """Single imported shot event from a launch monitor or shot-tracking export."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    player_id: str = Field(..., min_length=1, max_length=120)
    club: str = Field(..., min_length=1, max_length=40)
    carry_yds: float = Field(..., gt=0.0, le=400.0)
    total_yds: float = Field(..., gt=0.0, le=450.0)
    launch_speed_mph: float | None = Field(default=None, gt=0.0, le=250.0)
    spin_rpm: float | None = Field(default=None, ge=0.0, le=15000.0)
    offline_ft: float | None = Field(default=None, ge=-500.0, le=500.0)
    lie: LieType | None = Field(default=None)
    source: Literal["trackman", "foresight", "golfpad", "manual"]
    captured_at: datetime

    @field_validator("club", mode="before")
    @classmethod
    def _normalize_club(cls, value: Any) -> str:
        return canonicalize_club_name(str(value))

    @field_validator("carry_yds", "total_yds", "launch_speed_mph", "spin_rpm", "offline_ft", mode="before")
    @classmethod
    def _coerce_numeric(cls, value: Any) -> float | None:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            raise ValueError("Shot event numeric values must not be boolean.")
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Shot event numeric values must be numeric.") from exc

    @field_validator("carry_yds", "total_yds", "launch_speed_mph", "spin_rpm", "offline_ft")
    @classmethod
    def _round_numeric(cls, value: float | None) -> float | None:
        if value is None:
            return None
        return round(value, 1)

    @field_validator("captured_at", mode="before")
    @classmethod
    def _normalize_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            captured_at = value
        else:
            captured_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if captured_at.tzinfo is None:
            return captured_at.replace(tzinfo=timezone.utc)
        return captured_at.astimezone(timezone.utc)

