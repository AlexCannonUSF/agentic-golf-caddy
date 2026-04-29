"""Plays-like distance aggregation engine."""

from dataclasses import dataclass

from engine.elevation import calculate_elevation_adjustment
from engine.environment import calculate_altitude_adjustment, calculate_temperature_adjustment
from engine.lie import calculate_lie_adjustment
from engine.wind import calculate_wind_adjustment
from models import ShotContext
from utils.geometry import haversine_yards


@dataclass(frozen=True)
class DistanceBreakdown:
    """Detailed plays-like distance components."""

    actual_distance: float
    wind_adjustment: float
    elevation_adjustment: float
    lie_adjustment: float
    temperature_adjustment: float
    altitude_adjustment: float
    total_adjustment: float
    plays_like_distance: float

    @property
    def adjustments(self) -> dict[str, float]:
        """Return adjustment components in the shape expected by the UI."""

        return {
            "wind": self.wind_adjustment,
            "elevation": self.elevation_adjustment,
            "lie": self.lie_adjustment,
            "temperature": self.temperature_adjustment,
            "altitude": self.altitude_adjustment,
        }


def calculate_distance_breakdown(shot_context: ShotContext) -> DistanceBreakdown:
    """Compute full adjustment breakdown and plays-like distance."""

    actual_distance = shot_context.distance_to_target
    if (
        shot_context.target_mode.value == "pin"
        and shot_context.origin_lat_lon is not None
        and shot_context.pin_lat_lon is not None
    ):
        # A real pin coordinate is more precise than the manually entered
        # distance, so use it when the player is actually targeting the pin.
        actual_distance = haversine_yards(shot_context.origin_lat_lon, shot_context.pin_lat_lon)

    # Each adjustment is intentionally independent so tests can isolate the
    # reason a shot plays longer or shorter than the raw yardage.
    wind_adjustment = calculate_wind_adjustment(shot_context.wind_speed, shot_context.wind_direction)
    elevation_adjustment = calculate_elevation_adjustment(shot_context.elevation)
    lie_adjustment = calculate_lie_adjustment(shot_context.lie_type)
    temperature_adjustment = calculate_temperature_adjustment(shot_context.temperature)
    altitude_adjustment = calculate_altitude_adjustment(shot_context.altitude_ft)

    total_adjustment = round(
        wind_adjustment
        + elevation_adjustment
        + lie_adjustment
        + temperature_adjustment
        + altitude_adjustment,
        1,
    )
    plays_like_distance = round(actual_distance + total_adjustment, 1)

    return DistanceBreakdown(
        actual_distance=actual_distance,
        wind_adjustment=wind_adjustment,
        elevation_adjustment=elevation_adjustment,
        lie_adjustment=lie_adjustment,
        temperature_adjustment=temperature_adjustment,
        altitude_adjustment=altitude_adjustment,
        total_adjustment=total_adjustment,
        plays_like_distance=plays_like_distance,
    )


def calculate_plays_like_distance(shot_context: ShotContext) -> float:
    """Convenience wrapper returning only plays-like distance."""

    return calculate_distance_breakdown(shot_context).plays_like_distance
