"""Typed player profile model and related constants."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.agentic import PlayerTendencies
from models.enums import PreferredShot, SkillLevel

STANDARD_BAG_ORDER: tuple[str, ...] = (
    "Driver",
    "3-wood",
    "5-wood",
    "4-hybrid",
    "5-iron",
    "6-iron",
    "7-iron",
    "8-iron",
    "9-iron",
    "PW",
    "SW",
    "LW",
)

MIN_CLUBS_REQUIRED = 8

_TOKENIZED_STANDARD_NAMES = {
    re.sub(r"[^a-z0-9]+", "_", club.lower()).strip("_"): club for club in STANDARD_BAG_ORDER
}

_CLUB_ALIASES = {
    "3w": "3-wood",
    "5w": "5-wood",
    "4h": "4-hybrid",
    "5i": "5-iron",
    "6i": "6-iron",
    "7i": "7-iron",
    "8i": "8-iron",
    "9i": "9-iron",
    "pitching_wedge": "PW",
    "gap_wedge": "GW",
    "sand_wedge": "SW",
    "lob_wedge": "LW",
    "driver": "Driver",
}


def canonicalize_club_name(raw_name: str) -> str:
    """Normalize common club naming variants to consistent labels."""

    stripped = raw_name.strip()
    if not stripped:
        return stripped

    token = re.sub(r"[^a-z0-9]+", "_", stripped.lower()).strip("_")
    if token in _TOKENIZED_STANDARD_NAMES:
        return _TOKENIZED_STANDARD_NAMES[token]
    if token in _CLUB_ALIASES:
        return _CLUB_ALIASES[token]
    return stripped


class PlayerProfile(BaseModel):
    """User-specific club carry distances and preferences."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(..., min_length=1, max_length=80)
    skill_level: SkillLevel
    club_distances: dict[str, float]
    preferred_shot: PreferredShot = Field(default=PreferredShot.STRAIGHT)
    tendencies: PlayerTendencies = Field(default_factory=PlayerTendencies)

    @field_validator("club_distances", mode="before")
    @classmethod
    def _normalize_club_distances(cls, value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            raise TypeError("club_distances must be a mapping of club names to distances.")

        normalized: dict[str, float] = {}
        seen_names: set[str] = set()

        for raw_name, raw_distance in value.items():
            club_name = canonicalize_club_name(str(raw_name))
            if not club_name:
                raise ValueError("Club names cannot be empty.")

            lowered_name = club_name.lower()
            if lowered_name in seen_names:
                raise ValueError(f"Duplicate club name detected: {club_name}")
            seen_names.add(lowered_name)

            if isinstance(raw_distance, bool):
                raise ValueError(f"Distance for {club_name} must be numeric.")
            try:
                distance = float(raw_distance)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Distance for {club_name} must be numeric.") from exc

            normalized[club_name] = round(distance, 1)

        return normalized

    @field_validator("club_distances")
    @classmethod
    def _validate_club_distances(cls, value: dict[str, float]) -> dict[str, float]:
        if len(value) < MIN_CLUBS_REQUIRED:
            raise ValueError(
                f"At least {MIN_CLUBS_REQUIRED} clubs are required for reliable recommendations."
            )

        for club_name, distance in value.items():
            if distance <= 0.0:
                raise ValueError(f"Distance for {club_name} must be > 0.")
            if distance > 400.0:
                raise ValueError(f"Distance for {club_name} must be <= 400.")

        if all(club in value for club in STANDARD_BAG_ORDER):
            previous_distance = float("inf")
            for club in STANDARD_BAG_ORDER:
                current_distance = value[club]
                if current_distance >= previous_distance:
                    raise ValueError(
                        f"Club distances must be strictly decreasing in standard bag order. Problem at {club}."
                    )
                previous_distance = current_distance

        return value
