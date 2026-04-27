"""Typed course and hazard models for real-data integrations."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from models.environment import LatLon


class TeeBox(BaseModel):
    """A teeing area option for a hole."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    label: str = Field(..., min_length=1, max_length=80)
    color: str | None = Field(default=None, max_length=40)
    center: LatLon
    polygon: list[LatLon] = Field(default_factory=list)


class Green(BaseModel):
    """Green geometry and its derived center."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    center: LatLon
    polygon: list[LatLon] = Field(..., min_length=3)


class Hazard(BaseModel):
    """A hazard polygon associated with a hole."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    kind: Literal["bunker", "water", "ob", "trees"]
    center: LatLon
    polygon: list[LatLon] = Field(..., min_length=3)
    carry_distance_yds: float | None = Field(default=None, ge=0.0, le=900.0)


class Hole(BaseModel):
    """A playable golf hole with tee/green/fairway/hazard geometry."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    number: int = Field(..., ge=1, le=36)
    par: int = Field(default=4, ge=3, le=6)
    tees: list[TeeBox] = Field(default_factory=list)
    fairway_polygon: list[LatLon] = Field(..., min_length=3)
    green: Green
    hazards: list[Hazard] = Field(default_factory=list)


class Course(BaseModel):
    """Stored course representation derived from OSM/Overpass geometry."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    id: str = Field(..., min_length=1, max_length=120)
    name: str = Field(..., min_length=1, max_length=160)
    location: LatLon
    holes: list[Hole] = Field(..., min_length=1)
    osm_ref: str | None = Field(default=None, max_length=80)
    source: Literal["osm_overpass", "manual"] = "osm_overpass"
