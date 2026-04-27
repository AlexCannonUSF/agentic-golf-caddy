from engine.distance_engine import calculate_distance_breakdown, calculate_plays_like_distance
from models import ShotContext


def test_distance_breakdown_expected_values() -> None:
    context = ShotContext(
        distance_to_target=150,
        lie_type="rough",
        wind_speed=15,
        wind_direction="headwind",
        elevation="uphill",
        strategy="neutral",
        temperature=72,
        altitude_ft=0,
    )

    breakdown = calculate_distance_breakdown(context)

    assert breakdown.wind_adjustment == 18.0
    assert breakdown.elevation_adjustment == 5.0
    assert breakdown.lie_adjustment == 7.0
    assert breakdown.temperature_adjustment == 0.0
    assert breakdown.altitude_adjustment == 0.0
    assert breakdown.total_adjustment == 30.0
    assert breakdown.plays_like_distance == 180.0


def test_distance_breakdown_includes_environmental_adjustments() -> None:
    context = ShotContext(
        distance_to_target=200,
        lie_type="fairway",
        wind_speed=10,
        wind_direction="tailwind",
        elevation="downhill",
        strategy="neutral",
        temperature=45,
        altitude_ft=5000,
    )

    breakdown = calculate_distance_breakdown(context)

    # -5 (tailwind) + -5 (downhill) + 0 (lie) + 4.5 (cold) + -10 (altitude) = -15.5
    assert breakdown.total_adjustment == -15.5
    assert breakdown.plays_like_distance == 184.5
    assert calculate_plays_like_distance(context) == 184.5
