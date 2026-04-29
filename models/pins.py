# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Pin-placement models for daily course pin sheets."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.environment import LatLon


class HolePin(BaseModel):
    """Stored pin coordinate for a specific course hole and date."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    hole_number: int = Field(..., ge=1, le=36)
    pin_lat_lon: LatLon
    source: Literal["manual", "preset", "saved"] = "manual"
    updated_at: datetime

    @field_validator("updated_at", mode="before")
    @classmethod
    def _normalize_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            updated_at = value
        else:
            updated_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if updated_at.tzinfo is None:
            return updated_at.replace(tzinfo=timezone.utc)
        return updated_at.astimezone(timezone.utc)


class DailyPinSheet(BaseModel):
    """Collection of per-hole pin placements for one course and one date."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    course_id: str = Field(..., min_length=1, max_length=120)
    pin_date: date
    holes: list[HolePin] = Field(default_factory=list)
