"""Pre-loaded demo scenarios for quick form auto-fill."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    """A named shot scenario used to pre-fill the input form."""

    label: str
    description: str
    distance_to_target: float
    lie_type: str = "fairway"
    wind_speed: int = 0
    wind_direction: str = "headwind"
    elevation: str = "flat"
    strategy: str = "neutral"
    temperature: float = 72.0
    altitude_ft: float = 0.0
    target_mode: str = "pin"
    pin_position: str | None = None
    hazard_note: str | None = None
    player_confidence: int | None = None

    def to_dict(self) -> dict:
        return {
            "distance_to_target": self.distance_to_target,
            "lie_type": self.lie_type,
            "wind_speed": self.wind_speed,
            "wind_direction": self.wind_direction,
            "elevation": self.elevation,
            "strategy": self.strategy,
            "temperature": self.temperature,
            "altitude_ft": self.altitude_ft,
            "target_mode": self.target_mode,
            "pin_position": self.pin_position,
            "hazard_note": self.hazard_note,
            "player_confidence": self.player_confidence,
        }


SAMPLE_SCENARIOS: list[Scenario] = [
    Scenario(
        label="Calm Par 3",
        description="150 yds, fairway, no wind, flat",
        distance_to_target=150.0,
    ),
    Scenario(
        label="Windy Approach",
        description="160 yds, 20 mph headwind, uphill",
        distance_to_target=160.0,
        wind_speed=20,
        wind_direction="headwind",
        elevation="uphill",
        pin_position="back",
    ),
    Scenario(
        label="Tough Bunker Shot",
        description="85 yds, bunker, safe strategy",
        distance_to_target=85.0,
        lie_type="bunker",
        strategy="safe",
    ),
    Scenario(
        label="Downhill Risk/Reward",
        description="200 yds, steep downhill, aggressive",
        distance_to_target=200.0,
        elevation="steep_downhill",
        strategy="aggressive",
        hazard_note="trouble_long",
    ),
    Scenario(
        label="Cold Mountain Round",
        description="170 yds, 45°F, 5000 ft altitude",
        distance_to_target=170.0,
        temperature=45.0,
        altitude_ft=5000.0,
        target_mode="center_green",
    ),
]
