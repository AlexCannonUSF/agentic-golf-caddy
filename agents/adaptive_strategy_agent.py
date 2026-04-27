"""Adaptive strategy agent for bounded recommendation support."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path

from models import AdaptiveDecision, CandidateOption, LieType, PlayerProfile, PlayerTendencies, ShotContext, TargetMode

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_DEFAULT_PROMPT_FILE = _PROMPTS_DIR / "adaptive_strategy_prompt_v1.txt"


def _load_prompt_template(prompt_file: Path | None = None) -> str:
    path = prompt_file or _DEFAULT_PROMPT_FILE
    return path.read_text(encoding="utf-8")


def _extract_json_payload(text: str) -> dict[str, object]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _club_family(club_name: str) -> str:
    normalized = club_name.strip().lower()
    if normalized == "driver":
        return "driver"
    if "wood" in normalized:
        return "wood"
    if "hybrid" in normalized:
        return "hybrid"
    if normalized.endswith("iron"):
        prefix = normalized.split("-", 1)[0]
        try:
            iron_number = int(prefix)
        except ValueError:
            return "iron"
        if iron_number <= 5:
            return "long_iron"
        if iron_number <= 7:
            return "mid_iron"
        return "short_iron"
    if normalized in {"pw", "gw", "aw", "sw", "lw"}:
        return "wedge"
    return "other"


def _is_layup_safe_family(shot_context: ShotContext, club_name: str) -> bool:
    family = _club_family(club_name)

    if shot_context.lie_type == LieType.BUNKER:
        if family in {"driver", "wood"}:
            return False
        if shot_context.distance_to_target <= 190.0 and family == "hybrid":
            return False
        return True

    if shot_context.lie_type == LieType.DEEP_ROUGH:
        return family not in {"driver", "wood"}

    return True


def _forced_layup_choice(
    shot_context: ShotContext,
    candidate_options: list[CandidateOption],
) -> CandidateOption | None:
    if shot_context.target_mode == TargetMode.LAYUP:
        return None

    if shot_context.lie_type not in {LieType.BUNKER, LieType.DEEP_ROUGH}:
        return None

    safe_candidates = [option for option in candidate_options if _is_layup_safe_family(shot_context, option.club_name)]
    if not safe_candidates:
        return None

    longest_safe = max(safe_candidates, key=lambda option: option.club_distance)
    if longest_safe.club_distance >= shot_context.distance_to_target - 12.0:
        return None

    under_target = [option for option in safe_candidates if option.club_distance <= shot_context.distance_to_target]
    if under_target:
        return max(under_target, key=lambda option: option.club_distance)
    return min(safe_candidates, key=lambda option: option.distance_gap)


def _adaptive_risk_penalty(option: CandidateOption, shot_context: ShotContext) -> float:
    family = _club_family(option.club_name)
    penalty = 0.0

    if shot_context.lie_type == LieType.BUNKER:
        if family == "driver":
            penalty += 8.0
        elif family == "wood":
            penalty += 6.0
        elif family == "hybrid":
            penalty += 4.0
        elif family == "long_iron":
            penalty += 2.0
        if shot_context.distance_to_target <= 190.0 and family in {"wood", "hybrid", "long_iron"}:
            penalty += 3.0

    if shot_context.lie_type == LieType.DEEP_ROUGH:
        if family == "driver":
            penalty += 5.0
        elif family == "wood":
            penalty += 3.5
        elif family == "hybrid":
            penalty += 2.0

    if shot_context.player_confidence is not None and shot_context.player_confidence <= 2:
        if family in {"driver", "wood"}:
            penalty += 2.0

    return penalty


def _violates_guardrails(shot_context: ShotContext, club_name: str) -> bool:
    family = _club_family(club_name)
    if shot_context.lie_type == LieType.BUNKER:
        if family in {"driver", "wood"}:
            return True
        if shot_context.distance_to_target <= 190.0 and family == "hybrid":
            return True
    return False


def _coerce_guardrail_safe_choice(
    shot_context: ShotContext,
    candidate_options: list[CandidateOption],
    chosen: AdaptiveDecision,
) -> AdaptiveDecision:
    if not _violates_guardrails(shot_context, chosen.recommended_club):
        return chosen

    for option in candidate_options:
        if not _violates_guardrails(shot_context, option.club_name):
            return chosen.model_copy(
                update={
                    "recommended_club": option.club_name,
                    "strategy_rationale": (
                        f"{chosen.strategy_rationale} The final club was kept inside the bunker/lie guardrails."
                    ),
                    "risk_flags": list(dict.fromkeys([*chosen.risk_flags, "guardrail_override"])),
                }
            )

    return chosen


def _fallback_strategy(
    shot_context: ShotContext,
    candidate_options: list[CandidateOption],
    tendencies: PlayerTendencies,
) -> AdaptiveDecision:
    if not candidate_options:
        raise ValueError("AdaptiveStrategyAgent requires at least one candidate option.")

    forced_layup = _forced_layup_choice(shot_context, candidate_options)
    chosen = forced_layup or candidate_options[0]
    chosen_score = float("-inf")
    risk_flags: list[str] = []
    target_line = shot_context.target_mode.value.replace("_", " ")

    if forced_layup is not None:
        risk_flags.extend(["carry_not_realistic", "forced_layup"])
        target_line = "layup window"
        used_history = bool(
            tendencies.common_miss or tendencies.confidence_by_club or tendencies.dispersion_by_club
        )
        rationale = (
            f"Adaptive strategy shifted to a layup with {forced_layup.club_name} because the full carry "
            f"is not realistic from this {shot_context.lie_type.value.replace('_', ' ')} lie."
        )
        adaptive = AdaptiveDecision(
            recommended_club=forced_layup.club_name,
            target_line=target_line,
            strategy_rationale=rationale,
            risk_flags=risk_flags,
            used_history=used_history,
        )
        return _coerce_guardrail_safe_choice(shot_context, candidate_options, adaptive)

    for option in candidate_options:
        score = -option.distance_gap
        score -= _adaptive_risk_penalty(option, shot_context)

        if shot_context.target_mode == TargetMode.CENTER_GREEN:
            score += 1.5 if option.club_distance <= shot_context.distance_to_target else -0.5
            target_line = "center green"
        elif shot_context.target_mode == TargetMode.LAYUP:
            score += 3.0 if option.club_distance <= shot_context.distance_to_target else -2.0
            target_line = "layup window"

        hazard = (shot_context.hazard_note or "").lower()
        if "water" in hazard:
            score += 3.5 if option.club_distance <= shot_context.distance_to_target else -2.0
            if "water_hazard" not in risk_flags:
                risk_flags.append("water_hazard")
        if "ob" in hazard:
            score += 3.5 if option.club_distance <= shot_context.distance_to_target else -2.0
            if "out_of_bounds_risk" not in risk_flags:
                risk_flags.append("out_of_bounds_risk")
        if "bunker" in hazard:
            score += 1.0 if option.club_distance <= shot_context.distance_to_target else -0.5
        if "short" in hazard:
            score += 2.5 if option.club_distance >= shot_context.distance_to_target else -1.0
            if "must_carry_hazard" not in risk_flags:
                risk_flags.append("must_carry_hazard")
        if "long" in hazard:
            score += 2.5 if option.club_distance <= shot_context.distance_to_target else -1.0
            if "long_side_penalty" not in risk_flags:
                risk_flags.append("long_side_penalty")
        if "left" in hazard:
            target_line = "right-center"
            if "left_side_hazard" not in risk_flags:
                risk_flags.append("left_side_hazard")
        if "right" in hazard:
            target_line = "left-center"
            if "right_side_hazard" not in risk_flags:
                risk_flags.append("right_side_hazard")

        common_miss = (tendencies.common_miss or "").lower()
        if "short" in common_miss:
            score += 1.5 if option.club_distance >= shot_context.distance_to_target else -0.5
        if "long" in common_miss:
            score += 1.5 if option.club_distance <= shot_context.distance_to_target else -0.5

        confidence = tendencies.confidence_by_club.get(option.club_name)
        if confidence is not None:
            score += confidence * 2.0

        dispersion = tendencies.dispersion_by_club.get(option.club_name)
        if dispersion is not None:
            score -= dispersion / 25.0

        if shot_context.player_confidence is not None and shot_context.player_confidence <= 2:
            score += 1.0 if option.club_distance <= shot_context.distance_to_target else -0.75
            target_line = "center green"
            if "low_player_confidence" not in risk_flags:
                risk_flags.append("low_player_confidence")

        if score > chosen_score:
            chosen = option
            chosen_score = score

    used_history = bool(
        tendencies.common_miss or tendencies.confidence_by_club or tendencies.dispersion_by_club
    )
    rationale = (
        f"Adaptive strategy stayed within the deterministic shortlist and preferred {chosen.club_name} "
        f"because it best fits the target line, hazard context, and player tendencies."
    )
    if chosen.club_name == candidate_options[0].club_name and not risk_flags and not used_history:
        rationale = "Adaptive strategy kept the deterministic recommendation because no stronger context signal was present."

    adaptive = AdaptiveDecision(
        recommended_club=chosen.club_name,
        target_line=target_line,
        strategy_rationale=rationale,
        risk_flags=risk_flags,
        used_history=used_history,
    )
    return _coerce_guardrail_safe_choice(shot_context, candidate_options, adaptive)


class AdaptiveStrategyAgent:
    """Use bounded AI reasoning to re-rank deterministic club candidates."""

    def __init__(self, prompt_file: Path | None = None, model: str = "gpt-4o-mini") -> None:
        self._prompt_template = _load_prompt_template(prompt_file)
        self._model = model

    def _llm_strategy(
        self,
        shot_context: ShotContext,
        candidate_options: list[CandidateOption],
        tendencies: PlayerTendencies,
    ) -> AdaptiveDecision:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or OpenAI is None:
            raise RuntimeError("OpenAI not available for adaptive strategy.")

        client = OpenAI(api_key=api_key)
        candidate_blob = json.dumps([option.model_dump(mode="json") for option in candidate_options], indent=2)
        tendencies_blob = json.dumps(tendencies.model_dump(mode="json"), indent=2)
        shot_blob = json.dumps(shot_context.model_dump(mode="json"), indent=2)
        prompt = (
            self._prompt_template.replace("{candidate_options}", candidate_blob)
            .replace("{player_tendencies}", tendencies_blob)
            .replace("{shot_context}", shot_blob)
        )

        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=450,
        )
        payload = _extract_json_payload(response.choices[0].message.content or "")
        adaptive = AdaptiveDecision.model_validate(payload)

        allowed_clubs = {option.club_name for option in candidate_options}
        if adaptive.recommended_club not in allowed_clubs:
            raise ValueError("AdaptiveStrategyAgent LLM selected a club outside the allowed candidate list.")
        return _coerce_guardrail_safe_choice(shot_context, candidate_options, adaptive)

    def run(
        self,
        shot_context: ShotContext,
        candidate_options: list[CandidateOption],
        tendencies: PlayerTendencies,
    ) -> AdaptiveDecision:
        logger.info("AdaptiveStrategyAgent: evaluating bounded candidate set")
        forced_layup = _forced_layup_choice(shot_context, candidate_options)
        if forced_layup is not None:
            logger.info(
                "AdaptiveStrategyAgent: forcing layup with %s from %s lie",
                forced_layup.club_name,
                shot_context.lie_type.value,
            )
            return _fallback_strategy(shot_context, candidate_options, tendencies)
        try:
            adaptive = self._llm_strategy(shot_context, candidate_options, tendencies)
            logger.info("AdaptiveStrategyAgent: used LLM bounded strategy")
            return adaptive
        except RuntimeError as exc:
            logger.info("AdaptiveStrategyAgent: %s Falling back to heuristic strategy.", exc)
            return _fallback_strategy(shot_context, candidate_options, tendencies)
        except Exception:
            logger.exception("AdaptiveStrategyAgent: LLM strategy failed, using heuristic strategy")
            return _fallback_strategy(shot_context, candidate_options, tendencies)
