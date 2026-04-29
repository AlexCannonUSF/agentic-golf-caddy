# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
from engine.environment import calculate_altitude_adjustment, calculate_temperature_adjustment


def test_temperature_adjustments() -> None:
    assert calculate_temperature_adjustment(60) == 0.0
    assert calculate_temperature_adjustment(90) == 0.0
    assert calculate_temperature_adjustment(45) == 4.5
    assert calculate_temperature_adjustment(100) == -1.5


def test_altitude_adjustment() -> None:
    assert calculate_altitude_adjustment(0) == 0.0
    assert calculate_altitude_adjustment(500) == -1.0
    assert calculate_altitude_adjustment(5000) == -10.0
    assert calculate_altitude_adjustment(-250) == 0.0
