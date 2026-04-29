# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
from engine.confidence import score_confidence
from models import ConfidenceLevel, ShotContext


def _context(**updates):
    base = {
        "distance_to_target": 150,
        "lie_type": "fairway",
        "wind_speed": 10,
        "wind_direction": "headwind",
        "elevation": "flat",
        "strategy": "neutral",
        "temperature": 72,
        "altitude_ft": 0,
    }
    base.update(updates)
    return ShotContext(**base)


def test_confidence_thresholds_without_context() -> None:
    assert score_confidence(150, 154) == ConfidenceLevel.HIGH
    assert score_confidence(150, 159) == ConfidenceLevel.MEDIUM
    assert score_confidence(150, 170) == ConfidenceLevel.LOW


def test_extreme_wind_degrades_confidence() -> None:
    context = _context(wind_speed=35)
    assert score_confidence(150, 154, context) == ConfidenceLevel.MEDIUM


def test_deep_rough_and_steep_degrades_confidence() -> None:
    context = _context(lie_type="deep_rough", elevation="steep_uphill")
    assert score_confidence(150, 159, context) == ConfidenceLevel.LOW
