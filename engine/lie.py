# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Lie-based adjustment calculator."""

from models import LieType

_LIE_ADJUSTMENTS = {
    LieType.TEE: 0.0,
    LieType.FAIRWAY: 0.0,
    LieType.ROUGH: 7.0,
    LieType.DEEP_ROUGH: 15.0,
    LieType.BUNKER: 10.0,
}


def calculate_lie_adjustment(lie_type: LieType | str) -> float:
    """Return distance adjustment in yards from lie condition."""

    normalized = LieType(lie_type)
    return _LIE_ADJUSTMENTS[normalized]
