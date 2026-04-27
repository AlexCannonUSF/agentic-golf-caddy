import pytest

from utils.validators import InputValidationError, validate_shot_context_or_raise, validate_shot_input


def test_validate_shot_input_returns_context_for_valid_payload(sample_valid_shot_input) -> None:
    result = validate_shot_input(sample_valid_shot_input)

    assert result.is_valid
    assert result.shot_context is not None
    assert result.errors == tuple()
    assert result.shot_context.distance_to_target == 150.0


def test_validate_shot_input_normalizes_aliases_and_clamps_wind() -> None:
    result = validate_shot_input(
        {
            "distance_to_target": "165",
            "lie_type": "tee box",
            "wind_speed": -5,
            "wind_direction": "into",
            "elevation": "steep uphill",
            "strategy": "aggressive",
            "temperature": 70,
            "altitude_ft": 350,
        }
    )

    assert result.is_valid
    assert result.shot_context is not None
    assert result.shot_context.lie_type.value == "tee"
    assert result.shot_context.wind_direction.value == "headwind"
    assert result.shot_context.elevation.value == "steep_uphill"
    assert result.shot_context.wind_speed == 0.0


def test_validate_shot_input_accepts_optional_pin_locations() -> None:
    result = validate_shot_input(
        {
            "distance_to_target": 150,
            "origin_lat_lon": {"lat": 40.0, "lon": -73.0},
            "pin_lat_lon": {"lat": 40.0005, "lon": -73.001},
        }
    )

    assert result.is_valid
    assert result.shot_context is not None
    assert result.shot_context.pin_lat_lon is not None


def test_validate_shot_input_collects_multiple_errors() -> None:
    result = validate_shot_input(
        {
            "distance_to_target": "",
            "lie_type": "lava",
            "wind_speed": "not-a-number",
            "temperature": 200,
            "altitude_ft": -10,
        }
    )

    assert not result.is_valid
    assert len(result.errors) >= 5
    assert any("distance_to_target is required" in error for error in result.errors)
    assert any("lie_type must be one of" in error for error in result.errors)
    assert any("wind_speed must be numeric" in error for error in result.errors)


def test_validate_shot_context_or_raise_raises() -> None:
    with pytest.raises(InputValidationError) as exc:
        validate_shot_context_or_raise({"distance_to_target": "abc"})

    assert "distance_to_target must be numeric." in str(exc.value)
