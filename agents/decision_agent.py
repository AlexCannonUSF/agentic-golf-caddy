"""Agent 2: Caddy Decision Agent — computes plays-like distance and selects clubs."""

from __future__ import annotations

import logging

from engine.club_selector import ClubSelection, select_clubs
from engine.confidence import score_confidence
from engine.distance_engine import DistanceBreakdown, calculate_distance_breakdown
from models import CaddyDecision, PlayerProfile, ShotContext

logger = logging.getLogger(__name__)


class DecisionAgent:
    """Calculate plays-like distance and choose primary + backup clubs."""

    def run(self, shot_context: ShotContext, player_profile: PlayerProfile) -> CaddyDecision:
        """Return a fully populated CaddyDecision."""
        logger.info("DecisionAgent: computing distance breakdown")

        breakdown: DistanceBreakdown = calculate_distance_breakdown(shot_context)
        logger.debug(
            "DecisionAgent breakdown: plays_like=%.1f, adjustments=%s",
            breakdown.plays_like_distance,
            breakdown.adjustments,
        )

        selection: ClubSelection = select_clubs(
            breakdown.plays_like_distance,
            player_profile,
            shot_context.strategy,
            shot_context,
        )
        logger.debug(
            "DecisionAgent selection: primary=%s (%.0f), backup=%s (%.0f)",
            selection.primary_club,
            selection.primary_distance,
            selection.backup_club,
            selection.backup_distance,
        )

        confidence = score_confidence(
            breakdown.plays_like_distance,
            selection.primary_distance,
            shot_context,
        )
        logger.debug("DecisionAgent confidence: %s", confidence.value)

        decision = CaddyDecision(
            primary_club=selection.primary_club,
            backup_club=selection.backup_club,
            plays_like_distance=breakdown.plays_like_distance,
            actual_distance=breakdown.actual_distance,
            adjustments=breakdown.adjustments,
            confidence=confidence,
            strategy_note=selection.strategy_note,
        )

        logger.info(
            "DecisionAgent: recommend %s (backup %s), confidence=%s",
            decision.primary_club,
            decision.backup_club,
            decision.confidence.value,
        )
        return decision
