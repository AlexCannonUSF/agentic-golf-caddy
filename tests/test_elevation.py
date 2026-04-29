# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
from engine.elevation import calculate_elevation_adjustment


def test_elevation_adjustments() -> None:
    assert calculate_elevation_adjustment("flat") == 0.0
    assert calculate_elevation_adjustment("uphill") == 5.0
    assert calculate_elevation_adjustment("steep_uphill") == 10.0
    assert calculate_elevation_adjustment("downhill") == -5.0
    assert calculate_elevation_adjustment("steep_downhill") == -10.0
