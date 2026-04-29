# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Wind adjustment calculator."""

from models import WindDirection


def calculate_wind_adjustment(wind_speed: float, wind_direction: WindDirection | str) -> float:
    """
    Return distance adjustment in yards from wind conditions.

    Positive adjustment means the shot plays longer.
    Negative adjustment means the shot plays shorter.
    """

    speed = max(0.0, float(wind_speed))
    direction = WindDirection(wind_direction)

    if speed == 0.0:
        return 0.0

    if direction == WindDirection.HEADWIND:
        if speed <= 10.0:
            multiplier = 1.0
        elif speed <= 25.0:
            multiplier = 1.2
        else:
            multiplier = 1.5
        return round(speed * multiplier, 1)

    if direction == WindDirection.TAILWIND:
        multiplier = -0.5 if speed <= 10.0 else -0.6
        return round(speed * multiplier, 1)

    # Crosswinds slightly increase effective distance due to shot shape/control impact.
    return round(speed * 0.3, 1)
