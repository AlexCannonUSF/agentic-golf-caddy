# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
import pytest

from engine.wind import calculate_wind_adjustment


def test_headwind_tiers() -> None:
    assert calculate_wind_adjustment(0, "headwind") == 0.0
    assert calculate_wind_adjustment(5, "headwind") == 5.0
    assert calculate_wind_adjustment(10, "headwind") == 10.0
    assert calculate_wind_adjustment(11, "headwind") == 13.2
    assert calculate_wind_adjustment(25, "headwind") == 30.0
    assert calculate_wind_adjustment(26, "headwind") == 39.0


def test_tailwind_tiers() -> None:
    assert calculate_wind_adjustment(5, "tailwind") == -2.5
    assert calculate_wind_adjustment(10, "tailwind") == -5.0
    assert calculate_wind_adjustment(11, "tailwind") == -6.6


@pytest.mark.parametrize("direction", ["crosswind_left", "crosswind_right"])
def test_crosswind_adjustment(direction: str) -> None:
    assert calculate_wind_adjustment(15, direction) == 4.5


def test_negative_wind_speed_is_clamped_to_zero() -> None:
    assert calculate_wind_adjustment(-20, "headwind") == 0.0


def test_invalid_wind_direction_raises() -> None:
    with pytest.raises(ValueError):
        calculate_wind_adjustment(10, "nonsense")
