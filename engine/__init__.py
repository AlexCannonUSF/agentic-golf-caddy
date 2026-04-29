# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Core deterministic heuristics engine modules."""

from engine.club_selector import ClubSelection, rank_candidate_options, select_clubs
from engine.confidence import score_confidence
from engine.distance_engine import (
    DistanceBreakdown,
    calculate_distance_breakdown,
    calculate_plays_like_distance,
)
from engine.elevation import calculate_elevation_adjustment
from engine.environment import calculate_altitude_adjustment, calculate_temperature_adjustment
from engine.lie import calculate_lie_adjustment
from engine.wind import calculate_wind_adjustment

__all__ = [
    "ClubSelection",
    "DistanceBreakdown",
    "calculate_altitude_adjustment",
    "calculate_distance_breakdown",
    "calculate_elevation_adjustment",
    "calculate_lie_adjustment",
    "calculate_plays_like_distance",
    "calculate_temperature_adjustment",
    "calculate_wind_adjustment",
    "score_confidence",
    "rank_candidate_options",
    "select_clubs",
]
