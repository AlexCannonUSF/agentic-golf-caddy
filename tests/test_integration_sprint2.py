import itertools
from itertools import islice

import pytest

from engine import calculate_distance_breakdown, score_confidence, select_clubs
from models import ConfidenceLevel, Elevation, LieType, ShotContext, Strategy, WindDirection


def _surrounding_distances(club_distances: dict[str, float], target: float) -> tuple[float | None, float | None]:
    ordered = sorted(club_distances.values(), reverse=True)
    longer = None
    shorter = None

    for dist in ordered:
        if dist >= target:
            longer = dist
        else:
            shorter = dist
            break
    return longer, shorter


SCENARIOS = list(
    islice(
        itertools.product(
            [90, 120, 150, 180, 210, 240],
            [0, 8, 16],
            [WindDirection.HEADWIND, WindDirection.TAILWIND, WindDirection.CROSSWIND_LEFT],
            [LieType.FAIRWAY, LieType.ROUGH, LieType.BUNKER],
            [Elevation.FLAT, Elevation.UPHILL],
            [Strategy.SAFE, Strategy.NEUTRAL, Strategy.AGGRESSIVE],
        ),
        54,
    )
)


@pytest.mark.parametrize(
    "distance,wind_speed,wind_direction,lie,elevation,strategy",
    SCENARIOS,
)
def test_sprint2_end_to_end_matrix(
    sample_profile,
    distance,
    wind_speed,
    wind_direction,
    lie,
    elevation,
    strategy,
) -> None:
    context = ShotContext(
        distance_to_target=distance,
        lie_type=lie,
        wind_speed=wind_speed,
        wind_direction=wind_direction,
        elevation=elevation,
        strategy=strategy,
        temperature=72,
        altitude_ft=0,
    )

    breakdown = calculate_distance_breakdown(context)
    selection = select_clubs(breakdown.plays_like_distance, sample_profile, strategy)
    confidence = score_confidence(breakdown.plays_like_distance, selection.primary_distance, context)

    expected_plays_like = round(context.distance_to_target + sum(breakdown.adjustments.values()), 1)
    assert breakdown.plays_like_distance == expected_plays_like

    assert selection.primary_club in sample_profile.club_distances
    assert selection.backup_club in sample_profile.club_distances
    assert selection.primary_club != selection.backup_club

    assert selection.primary_distance == sample_profile.club_distances[selection.primary_club]
    assert selection.backup_distance == sample_profile.club_distances[selection.backup_club]

    assert confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW}

    longer, shorter = _surrounding_distances(sample_profile.club_distances, breakdown.plays_like_distance)
    if longer is not None and shorter is not None:
        if strategy == Strategy.SAFE:
            assert selection.primary_distance == shorter
        elif strategy == Strategy.AGGRESSIVE:
            assert selection.primary_distance == longer
        else:
            neutral_diff = abs(selection.primary_distance - breakdown.plays_like_distance)
            assert neutral_diff <= min(
                abs(longer - breakdown.plays_like_distance),
                abs(shorter - breakdown.plays_like_distance),
            )
