# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Environment and location models for real-data integrations."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LatLon(BaseModel):
    """Simple immutable geographic coordinate pair."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lat: float = Field(..., ge=-90.0, le=90.0)
    lon: float = Field(..., ge=-180.0, le=180.0)

    @field_validator("lat", "lon", mode="before")
    @classmethod
    def _coerce_numeric(cls, value: Any) -> float:
        if isinstance(value, bool):
            raise ValueError("Latitude and longitude must be numeric.")
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Latitude and longitude must be numeric.") from exc

    @field_validator("lat", "lon")
    @classmethod
    def _round_coordinate(cls, value: float) -> float:
        return round(value, 6)


class WeatherObservation(BaseModel):
    """Observed or forecast weather snapshot for a shot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    wind_speed_mph: float = Field(..., ge=0.0, le=120.0)
    wind_direction_deg: float = Field(..., ge=0.0, lt=360.0)
    temperature_f: float = Field(..., ge=-80.0, le=150.0)
    humidity_pct: float | None = Field(default=None, ge=0.0, le=100.0)
    pressure_mb: float | None = Field(default=None, ge=800.0, le=1100.0)
    source: Literal["open-meteo", "noaa", "manual"] = "manual"
    observed_at: datetime

    @field_validator("wind_speed_mph", "wind_direction_deg", "temperature_f", "humidity_pct", "pressure_mb", mode="before")
    @classmethod
    def _coerce_numeric(cls, value: Any) -> float | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool):
            raise ValueError("Weather values must be numeric.")
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Weather values must be numeric.") from exc

    @field_validator("wind_speed_mph", "wind_direction_deg", "temperature_f", "humidity_pct", "pressure_mb")
    @classmethod
    def _round_numeric(cls, value: float | None) -> float | None:
        if value is None:
            return None
        return round(value, 1)

    @field_validator("observed_at", mode="before")
    @classmethod
    def _normalize_timestamp(cls, value: Any) -> datetime:
        if isinstance(value, datetime):
            observed_at = value
        else:
            observed_at = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if observed_at.tzinfo is None:
            return observed_at.replace(tzinfo=timezone.utc)
        return observed_at.astimezone(timezone.utc)

