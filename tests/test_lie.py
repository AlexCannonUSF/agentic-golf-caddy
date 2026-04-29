# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
from engine.lie import calculate_lie_adjustment


def test_lie_adjustments() -> None:
    assert calculate_lie_adjustment("tee") == 0.0
    assert calculate_lie_adjustment("fairway") == 0.0
    assert calculate_lie_adjustment("rough") == 7.0
    assert calculate_lie_adjustment("deep_rough") == 15.0
    assert calculate_lie_adjustment("bunker") == 10.0
