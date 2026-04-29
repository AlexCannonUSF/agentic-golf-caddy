"""Agent 3: Coach/Explain Agent — generates human-readable recommendation explanations."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from models import AdaptiveDecision, CaddyDecision, Explanation, PlayerProfile, ShotContext

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_DEFAULT_PROMPT_FILE = _PROMPTS_DIR / "coach_prompt_v1.txt"


def _load_prompt_template(prompt_file: Path | None = None) -> str:
    """Read the prompt template from disk."""
    path = prompt_file or _DEFAULT_PROMPT_FILE
    return path.read_text(encoding="utf-8")


def _format_adjustments(adjustments: dict[str, float]) -> str:
    """Build a human-readable adjustment list sorted by magnitude."""
    if not adjustments:
        return "None"
    sorted_adj = sorted(adjustments.items(), key=lambda kv: abs(kv[1]), reverse=True)
    parts = [f"{name.capitalize()}: {value:+.1f} yds" for name, value in sorted_adj if value != 0.0]
    return ", ".join(parts) if parts else "None (all neutral)"


def _build_prompt(
    decision: CaddyDecision,
    shot_context: ShotContext,
    player_profile: PlayerProfile,
    prompt_template: str,
    adaptive_decision: AdaptiveDecision | None = None,
) -> str:
    """Fill the prompt template with shot data."""
    club_distances = player_profile.club_distances
    primary_dist = club_distances.get(decision.primary_club, decision.plays_like_distance)
    backup_dist = club_distances.get(decision.backup_club, decision.plays_like_distance)

    prompt = prompt_template.format(
        actual_distance=f"{decision.actual_distance:.0f}",
        plays_like_distance=f"{decision.plays_like_distance:.0f}",
        adjustments_formatted=_format_adjustments(decision.adjustments),
        primary_club=decision.primary_club,
        primary_distance=f"{primary_dist:.0f}",
        backup_club=decision.backup_club,
        backup_distance=f"{backup_dist:.0f}",
        strategy=shot_context.strategy.value,
        confidence=decision.confidence.value,
    )
    if adaptive_decision is not None:
        prompt += (
            "\n\nADAPTIVE STRATEGY CONTEXT:\n"
            f"- Target line: {adaptive_decision.target_line}\n"
            f"- Strategy rationale: {adaptive_decision.strategy_rationale}\n"
            f"- Risk flags: {', '.join(adaptive_decision.risk_flags) or 'none'}\n"
            "Use this context to make the recommendation feel more like a real caddie, "
            "but do not invent any new clubs or numbers.\n"
        )
    return prompt


def _template_fallback(
    decision: CaddyDecision,
    shot_context: ShotContext,
    player_profile: PlayerProfile,
    adaptive_decision: AdaptiveDecision | None = None,
) -> Explanation:
    """Generate a deterministic explanation without an LLM."""
    club_distances = player_profile.club_distances
    primary_dist = club_distances.get(decision.primary_club, decision.plays_like_distance)
    backup_dist = club_distances.get(decision.backup_club, decision.plays_like_distance)

    adj_text = _format_adjustments(decision.adjustments)
    lie_label = getattr(shot_context.lie_type, "value", str(shot_context.lie_type)).replace("_", " ")

    forced_layup = bool(
        adaptive_decision is not None
        and {"forced_layup", "carry_not_realistic"}.intersection(adaptive_decision.risk_flags)
    )

    # Layup explanations need different wording because the recommended club is
    # intentionally not trying to reach the full target.
    if forced_layup:
        summary = f"Take a layup with your {decision.primary_club}."
    else:
        summary = f"Use your {decision.primary_club}."

    if forced_layup:
        detail = (
            f"The shot is {decision.actual_distance:.0f} yards on paper, but the full carry plays too risky "
            f"from this {lie_label} lie. "
            f"Your {decision.primary_club} averages {primary_dist:.0f} yards, so the caddie is steering you "
            f"toward a controlled layup instead of forcing the number. "
            f"Confidence: {decision.confidence.value}."
        )
    else:
        detail = (
            f"The {decision.actual_distance:.0f}-yard shot plays like "
            f"{decision.plays_like_distance:.0f} yards after adjustments. "
            f"Your {decision.primary_club} averages {primary_dist:.0f} yards, "
            f"making it the best match for a {shot_context.strategy.value} strategy. "
            f"Confidence: {decision.confidence.value}."
        )
    if adaptive_decision is not None and adaptive_decision.strategy_rationale:
        detail += f" {adaptive_decision.strategy_rationale}"

    adjustment_breakdown = adj_text

    if forced_layup:
        backup_note = (
            f"If the lie feels better than expected, {decision.backup_club} "
            f"({backup_dist:.0f} avg) is the more aggressive fallback."
        )
    elif decision.plays_like_distance > primary_dist:
        backup_note = (
            f"If conditions feel tougher than expected, consider your "
            f"{decision.backup_club} ({backup_dist:.0f} avg) to ensure you reach the target."
        )
    else:
        backup_note = (
            f"If conditions ease up, your {decision.backup_club} "
            f"({backup_dist:.0f} avg) is a solid alternative."
        )

    return Explanation(
        summary=summary,
        detail=detail,
        adjustment_breakdown=adjustment_breakdown,
        backup_note=backup_note,
    )


def _parse_llm_response(
    response_text: str,
    decision: CaddyDecision,
    shot_context: ShotContext,
    player_profile: PlayerProfile,
    adaptive_decision: AdaptiveDecision | None = None,
) -> Explanation:
    """Parse raw LLM text into a structured Explanation.

    The LLM returns free-form prose so we split it into fields heuristically.
    If parsing fails we fall back to the template.
    """
    text = response_text.strip()
    if not text:
        logger.warning("CoachAgent: empty LLM response, using template fallback")
        return _template_fallback(decision, shot_context, player_profile, adaptive_decision)

    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]

    summary = (sentences[0] + ".") if sentences else f"Use your {decision.primary_club}."
    detail = text
    adjustment_breakdown = _format_adjustments(decision.adjustments)

    club_distances = player_profile.club_distances
    backup_dist = club_distances.get(decision.backup_club, decision.plays_like_distance)
    backup_note = (
        f"Backup: {decision.backup_club} ({backup_dist:.0f} avg) "
        f"if conditions change."
    )

    return Explanation(
        summary=summary,
        detail=detail,
        adjustment_breakdown=adjustment_breakdown,
        backup_note=backup_note,
    )


class CoachAgent:
    """Generate a human-readable explanation for a caddy decision.

    Uses the OpenAI API when ``OPENAI_API_KEY`` is set; otherwise falls back
    to a deterministic template.
    """

    def __init__(self, prompt_file: Path | None = None, model: str = "gpt-4o-mini") -> None:
        self._prompt_template = _load_prompt_template(prompt_file)
        self._model = model

    def run(
        self,
        decision: CaddyDecision,
        shot_context: ShotContext,
        player_profile: PlayerProfile,
        adaptive_decision: AdaptiveDecision | None = None,
    ) -> Explanation:
        """Produce an Explanation for the given decision."""
        logger.info("CoachAgent: generating explanation")

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            # The app is designed to be gradable without secrets. When no key is
            # configured, the deterministic explanation below still shows the
            # same numbers and reasoning.
            logger.info("CoachAgent: no OPENAI_API_KEY, using template fallback")
            return _template_fallback(decision, shot_context, player_profile, adaptive_decision)

        prompt = _build_prompt(
            decision,
            shot_context,
            player_profile,
            self._prompt_template,
            adaptive_decision,
        )
        logger.debug("CoachAgent prompt:\n%s", prompt)

        try:
            if OpenAI is None:
                logger.warning("CoachAgent: openai package not installed, using template fallback")
                return _template_fallback(decision, shot_context, player_profile, adaptive_decision)

            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=300,
            )
            response_text = response.choices[0].message.content or ""
            logger.info("CoachAgent: received LLM response (%d chars)", len(response_text))
            return _parse_llm_response(
                response_text,
                decision,
                shot_context,
                player_profile,
                adaptive_decision,
            )

        except RuntimeError as exc:
            logger.info("CoachAgent: %s Using template fallback.", exc)
            return _template_fallback(decision, shot_context, player_profile, adaptive_decision)
        except Exception:
            logger.exception("CoachAgent: LLM call failed, using template fallback")
            return _template_fallback(decision, shot_context, player_profile, adaptive_decision)
