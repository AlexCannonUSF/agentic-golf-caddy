# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Benchmark runner for deterministic, explanation, and bounded-hybrid variants."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from agents import CoachAgent, ContextAgent, DecisionAgent, Pipeline, VerifierAgent
from evaluation.benchmarks import load_adaptive_cases, load_clarification_cases, load_deterministic_cases
from evaluation.metrics import summarize_clarification_outcomes, summarize_scenario_outcomes
from evaluation.models import (
    ClarificationBenchmarkCase,
    ClarificationOutcome,
    EvaluationVariant,
    ScenarioBenchmarkCase,
    ScenarioOutcome,
)
from models import PlayerProfile
from utils import FeedbackManager, ProfileManager
from utils.validators import validate_shot_input


class _FailingCompletions:
    """Fake completions client used to test deterministic LLM fallbacks."""

    def create(self, *args: Any, **kwargs: Any) -> Any:
        """Always fail so the evaluation can measure fallback behavior."""

        raise RuntimeError("Simulated LLM failure for evaluation.")


class _FailingChat:
    """Fake chat client that exposes the failing completions object."""

    def __init__(self) -> None:
        self.completions = _FailingCompletions()


class _FailingOpenAIClient:
    """Minimal OpenAI-compatible client used inside failure-recovery tests."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.chat = _FailingChat()


class EvaluationRunner:
    """Run the checked-in benchmark suite against the selected profile."""

    def __init__(self, player_profile: PlayerProfile) -> None:
        self._player_profile = player_profile
        self._context_agent = ContextAgent()
        self._decision_agent = DecisionAgent()
        self._coach_agent = CoachAgent()
        self._verifier_agent = VerifierAgent()

    def _profile_for_case(
        self,
        case_id: str,
        profile_tendencies: Any = None,
    ) -> PlayerProfile:
        tendencies = profile_tendencies or self._player_profile.tendencies
        return self._player_profile.model_copy(
            deep=True,
            update={
                "name": f"{self._player_profile.name} [{case_id}]",
                "tendencies": tendencies,
            },
        )

    @staticmethod
    def _seed_feedback(
        manager: FeedbackManager,
        profile_name: str,
        case: ScenarioBenchmarkCase | ClarificationBenchmarkCase,
    ) -> None:
        for feedback in case.feedback_history:
            manager.add_feedback(profile_name, feedback)

    def _run_deterministic_case(
        self,
        case: ScenarioBenchmarkCase,
        *,
        include_explanation: bool,
    ) -> ScenarioOutcome:
        profile = self._profile_for_case(case.case_id, case.profile_tendencies)
        try:
            shot_context = self._context_agent.run(case.raw_input)
            decision = self._decision_agent.run(shot_context, profile)
        except Exception:
            return ScenarioOutcome(
                case_id=case.case_id,
                variant=(
                    EvaluationVariant.DETERMINISTIC_PLUS_EXPLANATION
                    if include_explanation
                    else EvaluationVariant.DETERMINISTIC_ONLY
                ),
                primary_club=None,
                backup_club=None,
                plays_like_distance=None,
                produced_valid_result=False,
            )

        explanation_grounded = None
        if include_explanation:
            explanation = self._coach_agent.run(decision, shot_context, profile)
            verification = self._verifier_agent.run(
                explanation,
                profile,
                primary_club=decision.primary_club,
                backup_club=decision.backup_club,
                actual_distance=decision.actual_distance,
                plays_like_distance=decision.plays_like_distance,
                adjustments=decision.adjustments,
            )
            explanation_grounded = verification.is_grounded

        return ScenarioOutcome(
            case_id=case.case_id,
            variant=(
                EvaluationVariant.DETERMINISTIC_PLUS_EXPLANATION
                if include_explanation
                else EvaluationVariant.DETERMINISTIC_ONLY
            ),
            primary_club=decision.primary_club,
            backup_club=decision.backup_club,
            plays_like_distance=decision.plays_like_distance,
            explanation_grounded=explanation_grounded,
            produced_valid_result=True,
        )

    def _run_bounded_hybrid_case(self, case: ScenarioBenchmarkCase) -> ScenarioOutcome:
        profile = self._profile_for_case(case.case_id, case.profile_tendencies)
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                manager = FeedbackManager(Path(tmp_dir) / "feedback.json")
                self._seed_feedback(manager, profile.name, case)

                pipeline = Pipeline(profile)
                pipeline._feedback_manager = manager
                result = pipeline.run(case.raw_input)
        except Exception:
            return ScenarioOutcome(
                case_id=case.case_id,
                variant=EvaluationVariant.BOUNDED_HYBRID,
                primary_club=None,
                backup_club=None,
                plays_like_distance=None,
                produced_valid_result=False,
            )

        produced_valid_result = bool(result.decision and result.explanation)
        return ScenarioOutcome(
            case_id=case.case_id,
            variant=EvaluationVariant.BOUNDED_HYBRID,
            primary_club=result.decision.primary_club if result.decision else None,
            backup_club=result.decision.backup_club if result.decision else None,
            plays_like_distance=result.decision.plays_like_distance if result.decision else None,
            explanation_grounded=result.verification.is_grounded if result.verification else None,
            corrected_output_used=result.verification.corrected_output_used if result.verification else False,
            produced_valid_result=produced_valid_result,
        )

    def run_scenario_benchmark(
        self,
        cases: list[ScenarioBenchmarkCase],
        variant: EvaluationVariant,
    ) -> dict[str, float | int]:
        """Run a structured benchmark for the requested variant."""

        if variant == EvaluationVariant.DETERMINISTIC_ONLY:
            outcomes = [self._run_deterministic_case(case, include_explanation=False) for case in cases]
        elif variant == EvaluationVariant.DETERMINISTIC_PLUS_EXPLANATION:
            outcomes = [self._run_deterministic_case(case, include_explanation=True) for case in cases]
        else:
            outcomes = [self._run_bounded_hybrid_case(case) for case in cases]

        return summarize_scenario_outcomes(cases, outcomes, self._player_profile)

    def _guess_without_clarification(
        self,
        pipeline: Pipeline,
        case: ClarificationBenchmarkCase,
        parsed_input: dict[str, Any],
        profile: PlayerProfile,
    ) -> str | None:
        validation = validate_shot_input(parsed_input)
        if validation.shot_context is None:
            return None

        decision = self._decision_agent.run(validation.shot_context, profile)
        return decision.primary_club

    def _run_clarification_case(self, case: ClarificationBenchmarkCase) -> ClarificationOutcome:
        profile = self._profile_for_case(case.case_id, case.profile_tendencies)
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                manager = FeedbackManager(Path(tmp_dir) / "feedback.json")
                self._seed_feedback(manager, profile.name, case)

                pipeline = Pipeline(profile)
                pipeline._feedback_manager = manager
                initial_result = pipeline.run({"shot_text": case.shot_text})

                asked = initial_result.needs_clarification
                question = initial_result.clarification.question if initial_result.clarification else None
                guessed = None
                if asked and initial_result.shot_intent:
                    merged_input = pipeline._merge_interpreted_input(
                        {"shot_text": case.shot_text},
                        initial_result.shot_intent,
                    )
                    guessed = self._guess_without_clarification(pipeline, case, merged_input, profile)
                elif initial_result.decision:
                    guessed = initial_result.decision.primary_club

                clarified_club = None
                if case.clarified_input:
                    clarified_result = pipeline.run(case.clarified_input)
                    if clarified_result.decision:
                        clarified_club = clarified_result.decision.primary_club

                final_club = clarified_club or (initial_result.decision.primary_club if initial_result.decision else None)
                produced_valid_result = bool(
                    initial_result.clarification if asked else initial_result.decision
                )
        except Exception:
            return ClarificationOutcome(
                case_id=case.case_id,
                asked_clarification=False,
                question=None,
                guessed_without_clarification=None,
                clarified_club=None,
                final_club=None,
                produced_valid_result=False,
            )

        return ClarificationOutcome(
            case_id=case.case_id,
            asked_clarification=asked,
            question=question,
            guessed_without_clarification=guessed,
            clarified_club=clarified_club,
            final_club=final_club,
            produced_valid_result=produced_valid_result,
        )

    def run_clarification_benchmark(
        self,
        cases: list[ClarificationBenchmarkCase],
    ) -> dict[str, float | int]:
        """Run the natural-language clarification benchmark."""

        outcomes = [self._run_clarification_case(case) for case in cases]
        return summarize_clarification_outcomes(cases, outcomes)

    def run_failure_recovery_check(
        self,
        scenario_cases: list[ScenarioBenchmarkCase],
        clarification_cases: list[ClarificationBenchmarkCase],
    ) -> dict[str, float | int]:
        """Simulate upstream LLM failures and verify bounded fallbacks hold up."""

        valid_results = 0
        total_cases = 0

        with patch.dict(os.environ, {"OPENAI_API_KEY": "evaluation-test-key"}, clear=False):
            with (
                patch("agents.input_interpreter_agent.OpenAI", _FailingOpenAIClient),
                patch("agents.adaptive_strategy_agent.OpenAI", _FailingOpenAIClient),
                patch("agents.coach_agent.OpenAI", _FailingOpenAIClient),
            ):
                for case in scenario_cases:
                    total_cases += 1
                    outcome = self._run_bounded_hybrid_case(case)
                    valid_results += int(outcome.produced_valid_result)

                for case in clarification_cases:
                    total_cases += 1
                    outcome = self._run_clarification_case(case)
                    valid_results += int(outcome.produced_valid_result)

        return {
            "cases": total_cases,
            "valid_results": valid_results,
            "fallback_reliability": round(valid_results / total_cases, 3) if total_cases else 0.0,
        }

    def run_all(self) -> dict[str, Any]:
        """Run the full starter evaluation suite and return a JSON-safe report."""

        deterministic_cases = load_deterministic_cases()
        adaptive_cases = load_adaptive_cases()
        clarification_cases = load_clarification_cases()

        deterministic_report = {
            variant.value: self.run_scenario_benchmark(deterministic_cases, variant)
            for variant in (
                EvaluationVariant.DETERMINISTIC_ONLY,
                EvaluationVariant.DETERMINISTIC_PLUS_EXPLANATION,
                EvaluationVariant.BOUNDED_HYBRID,
            )
        }
        adaptive_report = {
            variant.value: self.run_scenario_benchmark(adaptive_cases, variant)
            for variant in (
                EvaluationVariant.DETERMINISTIC_ONLY,
                EvaluationVariant.DETERMINISTIC_PLUS_EXPLANATION,
                EvaluationVariant.BOUNDED_HYBRID,
            )
        }
        adaptive_report["adaptive_lift"] = {
            "acceptable_set_accuracy": round(
                adaptive_report[EvaluationVariant.BOUNDED_HYBRID.value]["acceptable_set_accuracy"]
                - adaptive_report[EvaluationVariant.DETERMINISTIC_ONLY.value]["acceptable_set_accuracy"],
                3,
            ),
            "exact_club_accuracy": round(
                adaptive_report[EvaluationVariant.BOUNDED_HYBRID.value]["exact_club_accuracy"]
                - adaptive_report[EvaluationVariant.DETERMINISTIC_ONLY.value]["exact_club_accuracy"],
                3,
            ),
        }

        failure_recovery = self.run_failure_recovery_check(
            deterministic_cases + adaptive_cases,
            clarification_cases,
        )

        return {
            "profile_name": self._player_profile.name,
            "deterministic_scenarios": deterministic_report,
            "adaptive_scenarios": adaptive_report,
            "clarification_scenarios": self.run_clarification_benchmark(clarification_cases),
            "failure_recovery": failure_recovery,
        }


def load_profile(profile_name: str, profile_path: str | None = None) -> PlayerProfile:
    """Load either a default profile or a custom profile JSON file."""

    if profile_path:
        path = Path(profile_path)
        return PlayerProfile.model_validate_json(path.read_text(encoding="utf-8"))

    manager = ProfileManager(default_profiles_dir=Path(__file__).resolve().parents[1] / "profiles")
    return manager.load_default_profile(profile_name)


def main() -> int:
    """Run benchmarks from the command line and print JSON results."""

    parser = argparse.ArgumentParser(description="Run benchmark evaluation for Agentic Golf Caddy.")
    parser.add_argument(
        "--profile",
        default="intermediate",
        choices=("beginner", "intermediate", "advanced", "scratch"),
        help="Default profile to evaluate against.",
    )
    parser.add_argument(
        "--profile-file",
        default=None,
        help="Optional path to a custom player profile JSON file.",
    )
    args = parser.parse_args()

    profile = load_profile(args.profile, args.profile_file)
    report = EvaluationRunner(profile).run_all()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
