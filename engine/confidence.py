# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Confidence scoring for a club recommendation."""

from models import ConfidenceLevel, Elevation, LieType, ShotContext


def _degrade_confidence(level: ConfidenceLevel) -> ConfidenceLevel:
    if level == ConfidenceLevel.HIGH:
        return ConfidenceLevel.MEDIUM
    if level == ConfidenceLevel.MEDIUM:
        return ConfidenceLevel.LOW
    return ConfidenceLevel.LOW


def score_confidence(
    plays_like_distance: float,
    recommended_club_distance: float,
    shot_context: ShotContext | None = None,
) -> ConfidenceLevel:
    """
    Score confidence from distance fit and optional extreme-condition penalties.

    Baseline:
    - high: within +-5 yds
    - medium: within +-10 yds
    - low: > 10 yds off
    """

    diff = abs(float(recommended_club_distance) - float(plays_like_distance))
    # Start with a simple distance-fit score so confidence is easy to explain.
    if diff <= 5.0:
        level = ConfidenceLevel.HIGH
    elif diff <= 10.0:
        level = ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    if shot_context is None:
        return level

    # Difficult conditions reduce confidence even when the yardage fit is good.
    # This mirrors how a real caddie would treat wind, rough, and player comfort.
    extreme_wind = shot_context.wind_speed > 30.0
    steep_hill = shot_context.elevation in {Elevation.STEEP_UPHILL, Elevation.STEEP_DOWNHILL}
    deep_rough_and_steep = shot_context.lie_type == LieType.DEEP_ROUGH and steep_hill
    difficult_lie = shot_context.lie_type in {LieType.BUNKER, LieType.DEEP_ROUGH}
    low_player_confidence = shot_context.player_confidence is not None and shot_context.player_confidence <= 2

    if extreme_wind or deep_rough_and_steep:
        level = _degrade_confidence(level)
    if difficult_lie and diff > 5.0:
        level = _degrade_confidence(level)
    if low_player_confidence:
        level = _degrade_confidence(level)

    return level
