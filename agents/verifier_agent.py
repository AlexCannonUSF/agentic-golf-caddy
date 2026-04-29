# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Verifier agent that checks explanations for grounding issues."""

from __future__ import annotations

import logging
import re

from models import AdaptiveDecision, Explanation, PlayerProfile, VerificationResult

logger = logging.getLogger(__name__)


def _extract_numbers(text: str) -> list[float]:
    sanitized = re.sub(r"\b\d+-(?:iron|wood|hybrid)\b", "", text.lower())
    return [float(token) for token in re.findall(r"\b\d+(?:\.\d+)?\b", sanitized)]


class VerifierAgent:
    """Verify that the generated explanation stays grounded in pipeline outputs."""

    def run(
        self,
        explanation: Explanation,
        player_profile: PlayerProfile,
        *,
        primary_club: str,
        backup_club: str,
        actual_distance: float,
        plays_like_distance: float,
        adjustments: dict[str, float] | None = None,
        adaptive_decision: AdaptiveDecision | None = None,
    ) -> VerificationResult:
        """Check the final explanation for unsupported clubs or numbers."""

        allowed_clubs = {primary_club.lower(), backup_club.lower()}
        if adaptive_decision is not None:
            allowed_clubs.add(adaptive_decision.recommended_club.lower())

        club_names = sorted({club.lower() for club in player_profile.club_distances})
        combined_text = " ".join(
            [
                explanation.summary,
                explanation.detail,
                explanation.adjustment_breakdown,
                explanation.backup_note,
            ]
        ).lower()
        issues: list[str] = []

        mentioned_clubs = [club for club in club_names if club in combined_text]
        invalid_mentions = [club for club in mentioned_clubs if club not in allowed_clubs]
        if invalid_mentions:
            issues.append(f"Explanation referenced unsupported clubs: {', '.join(sorted(set(invalid_mentions)))}")

        allowed_numbers = {
            round(actual_distance, 1),
            round(plays_like_distance, 1),
            round(player_profile.club_distances.get(primary_club, 0.0), 1),
            round(player_profile.club_distances.get(backup_club, 0.0), 1),
        }
        for value in (adjustments or {}).values():
            if value != 0.0:
                allowed_numbers.add(round(abs(value), 1))
        for value in _extract_numbers(combined_text):
            if not any(abs(value - allowed) <= 1.0 for allowed in allowed_numbers):
                issues.append(f"Explanation referenced unsupported number: {value:g}")

        if issues:
            logger.warning("VerifierAgent: detected grounding issues: %s", issues)
            return VerificationResult(
                is_grounded=False,
                issues=issues,
                corrected_output_used=False,
            )

        return VerificationResult(
            is_grounded=True,
            issues=[],
            corrected_output_used=False,
        )
