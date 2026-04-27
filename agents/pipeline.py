"""Pipeline orchestrator — sequential Agent1 → Agent2 → Agent3 runner."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

from agents.adaptive_strategy_agent import AdaptiveStrategyAgent
from agents.clarification_agent import ClarificationAgent
from agents.coach_agent import CoachAgent, _template_fallback
from agents.context_agent import ContextAgent
from agents.decision_agent import DecisionAgent
from agents.input_interpreter_agent import InputInterpreterAgent
from agents.verifier_agent import VerifierAgent
from engine import rank_candidate_options, score_confidence
from models import (
    AdaptiveDecision,
    CandidateOption,
    CaddyDecision,
    ClarificationResult,
    Explanation,
    LieType,
    PlayerProfile,
    ShotContext,
    ShotIntent,
    VerificationResult,
)
from utils import FeedbackManager, RunRecorder
from utils.logger import PipelineLogger

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    """Complete output of a full pipeline run."""

    run_id: str | None = None
    shot_intent: ShotIntent | None = None
    clarification: ClarificationResult | None = None
    shot_context: ShotContext | None = None
    deterministic_decision: CaddyDecision | None = None
    decision: CaddyDecision | None = None
    candidate_options: list[CandidateOption] = field(default_factory=list)
    adaptive_decision: AdaptiveDecision | None = None
    explanation: Explanation | None = None
    verification: VerificationResult | None = None
    timing: dict[str, float] = field(default_factory=dict)

    @property
    def needs_clarification(self) -> bool:
        return bool(self.clarification and self.clarification.needs_clarification)


class Pipeline:
    """Sequential orchestrator: ContextAgent → DecisionAgent → CoachAgent.

    Parameters
    ----------
    player_profile:
        The active player profile used for club selection.
    debug:
        When *True*, structured JSON logs are emitted for each agent step
        via :class:`utils.logger.PipelineLogger`.
    """

    def __init__(
        self,
        player_profile: PlayerProfile,
        *,
        debug: bool = False,
    ) -> None:
        self._player_profile = player_profile
        self._input_interpreter_agent = InputInterpreterAgent()
        self._clarification_agent = ClarificationAgent()
        self._decision_agent = DecisionAgent()
        self._adaptive_strategy_agent = AdaptiveStrategyAgent()
        self._coach_agent = CoachAgent()
        self._verifier_agent = VerifierAgent()
        self._debug = debug
        self._feedback_manager = FeedbackManager()
        self._run_recorder = RunRecorder()
        self._pipeline_logger = PipelineLogger(enabled=debug)
        self._context_agent = ContextAgent(pipeline_logger=self._pipeline_logger)

    def _record_pipeline_result(
        self,
        *,
        run_id: str,
        raw_input: Mapping[str, Any],
        shot_intent: ShotIntent | None = None,
        clarification: ClarificationResult | None = None,
        shot_context: ShotContext | None = None,
        decision: CaddyDecision | None = None,
        adaptive_decision: AdaptiveDecision | None = None,
        explanation: Explanation | None = None,
        verification: VerificationResult | None = None,
        timing: dict[str, float] | None = None,
    ) -> None:
        try:
            self._run_recorder.record_pipeline_result(
                run_id=run_id,
                raw_input=dict(raw_input),
                player_profile=self._player_profile,
                shot_intent=shot_intent,
                clarification=clarification,
                shot_context=shot_context,
                decision=decision,
                adaptive_decision=adaptive_decision,
                explanation=explanation,
                verification=verification,
                timing_seconds=timing,
            )
        except Exception:
            logger.exception("Pipeline: failed to persist run record")

    def _merge_interpreted_input(
        self,
        raw_input: Mapping[str, Any],
        shot_intent: ShotIntent,
    ) -> dict[str, Any]:
        merged = {
            key: value
            for key, value in raw_input.items()
            if key != "shot_text" and value not in (None, "")
        }
        merged.update({key: value for key, value in shot_intent.parsed_fields.items() if value is not None})

        if shot_intent.course_context.target_mode:
            merged.setdefault("target_mode", shot_intent.course_context.target_mode.value)
        if shot_intent.course_context.pin_position is not None:
            merged.setdefault("pin_position", shot_intent.course_context.pin_position.value)
        if shot_intent.course_context.hazard_note:
            merged.setdefault("hazard_note", shot_intent.course_context.hazard_note)

        goal = shot_intent.user_intent.goal
        if goal == "middle_of_green":
            merged.setdefault("target_mode", "center_green")
        elif goal == "layup":
            merged.setdefault("target_mode", "layup")
        elif goal == "must_carry" and "hazard_note" not in merged:
            merged["hazard_note"] = "must_carry"

        return merged

    def _apply_adaptive_decision(
        self,
        decision: CaddyDecision,
        adaptive_decision: AdaptiveDecision,
        shot_context: ShotContext,
    ) -> CaddyDecision:
        if adaptive_decision.recommended_club not in self._player_profile.club_distances:
            return decision

        primary_club = adaptive_decision.recommended_club
        backup_club = decision.backup_club
        if primary_club != decision.primary_club:
            backup_club = decision.primary_club

        club_distance = self._player_profile.club_distances[primary_club]
        confidence = score_confidence(decision.plays_like_distance, club_distance, shot_context)

        return CaddyDecision(
            primary_club=primary_club,
            backup_club=backup_club,
            plays_like_distance=decision.plays_like_distance,
            actual_distance=decision.actual_distance,
            adjustments=decision.adjustments,
            confidence=confidence,
            strategy_note=adaptive_decision.strategy_rationale,
        )

    def run(self, raw_input: Mapping[str, Any]) -> PipelineResult:
        """Execute the full 3-agent pipeline and return results.

        Raises
        ------
        utils.validators.InputValidationError
            If Agent 1 rejects the raw input.
        """
        run_id = self._run_recorder.new_run_id()
        timing: dict[str, float] = {}
        active_profile = self._player_profile.model_copy(
            deep=True,
            update={
                "tendencies": self._feedback_manager.summarize_tendencies(self._player_profile),
            },
        )

        logger.info("Pipeline: starting run")
        self._pipeline_logger.log_step("pipeline_start", {"raw_input": dict(raw_input)})

        # ── Agent 0: Input Interpreter ────────────────────────────────
        t0 = time.perf_counter()
        shot_intent = self._input_interpreter_agent.run(raw_input)
        timing["input_interpreter_agent"] = round(time.perf_counter() - t0, 4)

        self._pipeline_logger.log_step(
            "input_interpreter_agent_done",
            {
                "shot_intent": shot_intent.model_dump(mode="json"),
                "elapsed_s": timing["input_interpreter_agent"],
            },
        )

        # ── Agent 0.5: Clarification ──────────────────────────────────
        t0 = time.perf_counter()
        clarification = self._clarification_agent.run(shot_intent, active_profile)
        timing["clarification_agent"] = round(time.perf_counter() - t0, 4)

        self._pipeline_logger.log_step(
            "clarification_agent_done",
            {
                "clarification": clarification.model_dump(mode="json"),
                "elapsed_s": timing["clarification_agent"],
            },
        )

        if clarification.needs_clarification:
            timing["total"] = round(sum(timing.values()), 4)
            logger.info("Pipeline: clarification required before decision")
            self._record_pipeline_result(
                run_id=run_id,
                raw_input=raw_input,
                shot_intent=shot_intent,
                clarification=clarification,
                timing=timing,
            )
            return PipelineResult(
                run_id=run_id,
                shot_intent=shot_intent,
                clarification=clarification,
                timing=timing,
            )

        interpreted_input = self._merge_interpreted_input(raw_input, shot_intent)

        # ── Agent 1: Context ──────────────────────────────────────────
        t0 = time.perf_counter()
        shot_context = self._context_agent.run(interpreted_input)
        timing["context_agent"] = round(time.perf_counter() - t0, 4)

        self._pipeline_logger.log_step(
            "context_agent_done",
            {
                "shot_context": shot_context.model_dump(mode="json"),
                "elapsed_s": timing["context_agent"],
            },
        )

        # ── Agent 2: Deterministic Decision ───────────────────────────
        t0 = time.perf_counter()
        deterministic_decision = self._decision_agent.run(shot_context, active_profile)
        timing["decision_agent"] = round(time.perf_counter() - t0, 4)

        self._pipeline_logger.log_step(
            "decision_agent_done",
            {
                "decision": deterministic_decision.model_dump(mode="json"),
                "elapsed_s": timing["decision_agent"],
            },
        )

        candidate_limit = 3
        if shot_context.lie_type in {LieType.BUNKER, LieType.DEEP_ROUGH} and shot_context.distance_to_target >= 160.0:
            candidate_limit = 5

        candidate_options = rank_candidate_options(
            deterministic_decision.plays_like_distance,
            active_profile,
            limit=candidate_limit,
            shot_context=shot_context,
        )
        tendencies = active_profile.tendencies

        # ── Agent 3: Adaptive Strategy ────────────────────────────────
        t0 = time.perf_counter()
        adaptive_decision = self._adaptive_strategy_agent.run(shot_context, candidate_options, tendencies)
        timing["adaptive_strategy_agent"] = round(time.perf_counter() - t0, 4)

        self._pipeline_logger.log_step(
            "adaptive_strategy_agent_done",
            {
                "adaptive_decision": adaptive_decision.model_dump(mode="json"),
                "candidate_options": [option.model_dump(mode="json") for option in candidate_options],
                "elapsed_s": timing["adaptive_strategy_agent"],
            },
        )

        decision = self._apply_adaptive_decision(deterministic_decision, adaptive_decision, shot_context)

        # ── Agent 4: Coach ────────────────────────────────────────────
        t0 = time.perf_counter()
        explanation = self._coach_agent.run(
            decision,
            shot_context,
            active_profile,
            adaptive_decision=adaptive_decision,
        )
        timing["coach_agent"] = round(time.perf_counter() - t0, 4)

        self._pipeline_logger.log_step(
            "coach_agent_done",
            {
                "explanation": explanation.model_dump(mode="json"),
                "elapsed_s": timing["coach_agent"],
            },
        )

        # ── Agent 5: Verifier ─────────────────────────────────────────
        t0 = time.perf_counter()
        verification = self._verifier_agent.run(
            explanation,
            active_profile,
            primary_club=decision.primary_club,
            backup_club=decision.backup_club,
            actual_distance=decision.actual_distance,
            plays_like_distance=decision.plays_like_distance,
            adjustments=decision.adjustments,
            adaptive_decision=adaptive_decision,
        )
        if not verification.is_grounded:
            explanation = _template_fallback(decision, shot_context, active_profile, adaptive_decision)
            verification = VerificationResult(
                is_grounded=True,
                issues=verification.issues,
                corrected_output_used=True,
            )
        timing["verifier_agent"] = round(time.perf_counter() - t0, 4)

        self._pipeline_logger.log_step(
            "verifier_agent_done",
            {
                "verification": verification.model_dump(mode="json"),
                "elapsed_s": timing["verifier_agent"],
            },
        )

        timing["total"] = round(sum(timing.values()), 4)
        self._pipeline_logger.log_step("pipeline_done", {"timing": timing})
        logger.info("Pipeline: completed in %.4fs", timing["total"])
        self._record_pipeline_result(
            run_id=run_id,
            raw_input=raw_input,
            shot_intent=shot_intent,
            clarification=clarification,
            shot_context=shot_context,
            decision=decision,
            adaptive_decision=adaptive_decision,
            explanation=explanation,
            verification=verification,
            timing=timing,
        )

        return PipelineResult(
            run_id=run_id,
            shot_intent=shot_intent,
            clarification=clarification,
            shot_context=shot_context,
            deterministic_decision=deterministic_decision,
            decision=decision,
            candidate_options=candidate_options,
            adaptive_decision=adaptive_decision,
            explanation=explanation,
            verification=verification,
            timing=timing,
        )
