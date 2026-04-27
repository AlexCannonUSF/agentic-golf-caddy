"""Clarification agent that asks follow-up questions only when needed."""

from __future__ import annotations

import logging

from engine import rank_candidate_options
from models import ClarificationResult, PlayerProfile, ShotIntent
from utils.validators import validate_shot_input

logger = logging.getLogger(__name__)

_QUESTION_BY_FIELD = {
    "distance_to_target": "How many yards do you have to the target?",
    "wind_speed": "About how strong is the wind right now?",
    "lie_type": "Would you call the lie fairway, rough, deep rough, or bunker?",
    "pin_position": "Is the pin front, middle, or back?",
    "target_mode": "Are you trying to hit the pin, play center green, or lay up?",
    "hazard_note": "Is there a hazard you are trying to avoid, like water short or trouble long?",
}

_HIGH_IMPACT_FIELDS = ("distance_to_target", "wind_speed", "lie_type", "pin_position", "target_mode", "hazard_note")


class ClarificationAgent:
    """Determine whether ambiguity is large enough to justify a follow-up question."""

    def run(self, shot_intent: ShotIntent, player_profile: PlayerProfile) -> ClarificationResult:
        if shot_intent.raw_text == "[structured_input]":
            return ClarificationResult(
                needs_clarification=False,
                question=None,
                reason="Structured input was supplied directly.",
                decision_sensitivity=0.0,
            )

        if shot_intent.missing_fields:
            field_name = shot_intent.missing_fields[0]
            return ClarificationResult(
                needs_clarification=True,
                question=_QUESTION_BY_FIELD.get(field_name, "Can you clarify that shot detail?"),
                reason=f"Missing required field: {field_name}.",
                decision_sensitivity=1.0,
            )

        validation = validate_shot_input(shot_intent.parsed_fields)
        if validation.shot_context is None:
            return ClarificationResult(
                needs_clarification=True,
                question="Can you clarify the shot details a bit more before I recommend a club?",
                reason="Parsed free-text input did not validate cleanly.",
                decision_sensitivity=0.9,
            )

        candidates = rank_candidate_options(
            validation.shot_context.distance_to_target,
            player_profile,
            limit=2,
            shot_context=validation.shot_context,
        )
        if len(candidates) >= 2:
            club_gap = abs(candidates[0].club_distance - candidates[1].club_distance)
            decision_sensitivity = round(max(0.0, min(1.0, 1.0 - (club_gap / 20.0))), 2)
        else:
            decision_sensitivity = 0.2

        for field_name in _HIGH_IMPACT_FIELDS:
            if field_name in shot_intent.ambiguous_fields and decision_sensitivity >= 0.45:
                logger.info("ClarificationAgent: asking follow-up for %s", field_name)
                return ClarificationResult(
                    needs_clarification=True,
                    question=_QUESTION_BY_FIELD.get(field_name, "Can you clarify that shot detail?"),
                    reason=f"Uncertainty in {field_name} could change the club recommendation.",
                    decision_sensitivity=decision_sensitivity,
                )

        return ClarificationResult(
            needs_clarification=False,
            question=None,
            reason="Parsed shot context is specific enough to proceed.",
            decision_sensitivity=decision_sensitivity,
        )
