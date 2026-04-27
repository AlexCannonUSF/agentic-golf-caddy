"""Metric helpers for benchmark evaluation."""

from __future__ import annotations

from typing import Iterable

from evaluation.models import ClarificationBenchmarkCase, ClarificationOutcome, ScenarioBenchmarkCase, ScenarioOutcome
from models import PlayerProfile, STANDARD_BAG_ORDER


def _round_metric(value: float) -> float:
    return round(value, 3)


def _ordered_clubs(profile: PlayerProfile) -> list[str]:
    if all(club in profile.club_distances for club in STANDARD_BAG_ORDER):
        return list(STANDARD_BAG_ORDER)
    return [
        club_name
        for club_name, _ in sorted(
            profile.club_distances.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


def is_within_one_club(predicted_club: str | None, expected_club: str, profile: PlayerProfile) -> bool:
    """Return True when the prediction is at most one bag slot away."""

    if not predicted_club:
        return False

    ordered = _ordered_clubs(profile)
    try:
        predicted_index = ordered.index(predicted_club)
        expected_index = ordered.index(expected_club)
    except ValueError:
        return False
    return abs(predicted_index - expected_index) <= 1


def summarize_scenario_outcomes(
    cases: Iterable[ScenarioBenchmarkCase],
    outcomes: Iterable[ScenarioOutcome],
    profile: PlayerProfile,
) -> dict[str, float | int]:
    """Aggregate structured scenario predictions into reportable metrics."""

    case_list = list(cases)
    outcome_map = {outcome.case_id: outcome for outcome in outcomes}
    total_cases = len(case_list)

    exact_hits = 0
    within_one_hits = 0
    acceptable_hits = 0
    valid_results = 0
    grounded_values: list[float] = []
    mae_values: list[float] = []

    for case in case_list:
        outcome = outcome_map.get(case.case_id)
        predicted = outcome.primary_club if outcome else None

        if outcome and outcome.produced_valid_result:
            valid_results += 1

        if predicted == case.expected_club:
            exact_hits += 1
        if is_within_one_club(predicted, case.expected_club, profile):
            within_one_hits += 1
        if predicted in case.acceptable_clubs:
            acceptable_hits += 1

        if outcome and outcome.explanation_grounded is not None:
            grounded_values.append(1.0 if outcome.explanation_grounded else 0.0)

        if (
            outcome
            and outcome.plays_like_distance is not None
            and case.expected_plays_like_distance is not None
        ):
            mae_values.append(abs(outcome.plays_like_distance - case.expected_plays_like_distance))

    return {
        "cases": total_cases,
        "exact_club_accuracy": _round_metric(exact_hits / total_cases) if total_cases else 0.0,
        "within_one_club_accuracy": _round_metric(within_one_hits / total_cases) if total_cases else 0.0,
        "acceptable_set_accuracy": _round_metric(acceptable_hits / total_cases) if total_cases else 0.0,
        "plays_like_distance_mae": _round_metric(sum(mae_values) / len(mae_values)) if mae_values else 0.0,
        "grounded_explanation_rate": (
            _round_metric(sum(grounded_values) / len(grounded_values)) if grounded_values else 0.0
        ),
        "valid_output_rate": _round_metric(valid_results / total_cases) if total_cases else 0.0,
    }


def summarize_clarification_outcomes(
    cases: Iterable[ClarificationBenchmarkCase],
    outcomes: Iterable[ClarificationOutcome],
) -> dict[str, float | int]:
    """Aggregate clarification behavior metrics."""

    case_list = list(cases)
    outcome_map = {outcome.case_id: outcome for outcome in outcomes}

    asked_count = 0
    true_positive_asks = 0
    useful_asks = 0
    question_focus_hits = 0
    question_focus_checks = 0
    valid_results = 0
    final_accuracy_hits = 0

    expected_asks = sum(1 for case in case_list if case.expected_needs_clarification)

    for case in case_list:
        outcome = outcome_map[case.case_id]

        if outcome.produced_valid_result:
            valid_results += 1

        if outcome.asked_clarification:
            asked_count += 1
            if case.expected_needs_clarification:
                true_positive_asks += 1

            if case.expected_question_contains:
                question_focus_checks += 1
                question_text = (outcome.question or "").lower()
                if case.expected_question_contains.lower() in question_text:
                    question_focus_hits += 1

        acceptable_final = set(case.acceptable_final_clubs)
        if case.expected_final_club:
            acceptable_final.add(case.expected_final_club)

        if outcome.final_club in acceptable_final:
            final_accuracy_hits += 1

        guessed_ok = outcome.guessed_without_clarification in acceptable_final
        clarified_ok = outcome.clarified_club in acceptable_final
        if case.expected_needs_clarification and outcome.asked_clarification and clarified_ok and not guessed_ok:
            useful_asks += 1

    return {
        "cases": len(case_list),
        "clarification_precision": _round_metric(true_positive_asks / asked_count) if asked_count else 0.0,
        "clarification_recall": _round_metric(true_positive_asks / expected_asks) if expected_asks else 0.0,
        "clarification_utility": _round_metric(useful_asks / expected_asks) if expected_asks else 0.0,
        "question_focus_accuracy": (
            _round_metric(question_focus_hits / question_focus_checks) if question_focus_checks else 0.0
        ),
        "final_decision_accuracy": (
            _round_metric(final_accuracy_hits / len(case_list)) if case_list else 0.0
        ),
        "valid_output_rate": _round_metric(valid_results / len(case_list)) if case_list else 0.0,
    }

