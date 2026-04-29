# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Metrics and reporting helpers for real recorded recommendation runs."""

from __future__ import annotations

from collections import Counter
from typing import Iterable

from models import ConfidenceLevel, RecommendationRating, RunRecord, ShotOutcome

_SUCCESS_OUTCOMES = {ShotOutcome.ON_TARGET, ShotOutcome.GOOD_CONTACT}
_DIRECTIONAL_EVAL_OUTCOMES = {
    ShotOutcome.ON_TARGET,
    ShotOutcome.GOOD_CONTACT,
    ShotOutcome.LEFT,
    ShotOutcome.RIGHT,
}
_CONFIDENCE_PROBABILITY = {
    ConfidenceLevel.HIGH: 0.85,
    ConfidenceLevel.MEDIUM: 0.6,
    ConfidenceLevel.LOW: 0.35,
}


def _round(value: float) -> float:
    return round(value, 3)


def summarize_real_runs(records: Iterable[RunRecord]) -> dict[str, object]:
    """Aggregate logged real-world runs into reportable metrics."""

    record_list = list(records)
    completed_runs = [record for record in record_list if record.decision is not None]
    feedback_runs = [record for record in completed_runs if record.outcome is not None]
    rated_runs = [
        record for record in feedback_runs if record.outcome and record.outcome.recommendation_rating is not None
    ]
    directional_runs = [
        record
        for record in feedback_runs
        if record.outcome and record.outcome.outcome in _DIRECTIONAL_EVAL_OUTCOMES
    ]

    primary_hits = sum(
        1
        for record in feedback_runs
        if record.decision is not None and record.outcome is not None and record.decision.primary_club == record.outcome.club_used
    )
    backup_hits = sum(
        1
        for record in feedback_runs
        if record.decision is not None and record.outcome is not None and record.decision.backup_club == record.outcome.club_used
    )
    good_call_hits = sum(
        1
        for record in rated_runs
        if record.outcome is not None and record.outcome.recommendation_rating == RecommendationRating.GOOD_CALL
    )
    directional_hits = sum(
        1
        for record in directional_runs
        if record.outcome is not None and record.outcome.outcome not in {ShotOutcome.LEFT, ShotOutcome.RIGHT}
    )

    brier_values: list[float] = []
    confidence_bucket_stats: dict[str, dict[str, float | int]] = {}
    for level in ConfidenceLevel:
        confidence_bucket_stats[level.value] = {
            "runs": 0,
            "success_rate": 0.0,
            "predicted_success_probability": _CONFIDENCE_PROBABILITY[level],
        }

    bucket_success_counter: Counter[str] = Counter()
    outcome_counter: Counter[str] = Counter()
    for record in feedback_runs:
        if record.decision is None or record.outcome is None:
            continue
        confidence = record.decision.confidence
        probability = _CONFIDENCE_PROBABILITY[confidence]
        success = 1.0 if record.outcome.outcome in _SUCCESS_OUTCOMES else 0.0
        brier_values.append((probability - success) ** 2)
        confidence_bucket_stats[confidence.value]["runs"] += 1
        bucket_success_counter[confidence.value] += int(success)
        outcome_counter[record.outcome.outcome.value] += 1

    for level in ConfidenceLevel:
        bucket_runs = int(confidence_bucket_stats[level.value]["runs"])
        if bucket_runs:
            confidence_bucket_stats[level.value]["success_rate"] = _round(
                bucket_success_counter[level.value] / bucket_runs
            )

    latency_totals = [record.latency_ms.get("total") for record in completed_runs if record.latency_ms.get("total") is not None]
    promotable_runs = sum(
        1
        for record in feedback_runs
        if record.outcome is not None and record.outcome.recommendation_rating is not None
    )

    return {
        "total_runs": len(record_list),
        "completed_runs": len(completed_runs),
        "feedback_linked_runs": len(feedback_runs),
        "rated_runs": len(rated_runs),
        "primary_club_agreement": _round(primary_hits / len(feedback_runs)) if feedback_runs else 0.0,
        "backup_club_agreement": _round(backup_hits / len(feedback_runs)) if feedback_runs else 0.0,
        "good_call_rate": _round(good_call_hits / len(rated_runs)) if rated_runs else 0.0,
        "directional_hit_rate": _round(directional_hits / len(directional_runs)) if directional_runs else 0.0,
        "confidence_calibration_brier": _round(sum(brier_values) / len(brier_values)) if brier_values else 0.0,
        "avg_total_latency_ms": _round(sum(latency_totals) / len(latency_totals)) if latency_totals else 0.0,
        "promotable_runs": promotable_runs,
        "confidence_buckets": confidence_bucket_stats,
        "outcome_breakdown": dict(sorted(outcome_counter.items())),
    }


def render_real_run_report(summary: dict[str, object]) -> str:
    """Return a markdown report for the real-run summary."""

    confidence_buckets = summary.get("confidence_buckets", {})
    outcome_breakdown = summary.get("outcome_breakdown", {})

    lines = [
        "# Real Run Evaluation Report",
        "",
        "## Summary",
        f"- Total logged runs: {summary['total_runs']}",
        f"- Completed recommendation runs: {summary['completed_runs']}",
        f"- Runs with linked feedback: {summary['feedback_linked_runs']}",
        f"- Rated runs (`good_call` / `bad_call`): {summary['rated_runs']}",
        f"- Promotable benchmark candidates: {summary['promotable_runs']}",
        f"- Average total latency: {summary['avg_total_latency_ms']} ms",
        "",
        "## Agreement Metrics",
        f"- Primary-club agreement: {summary['primary_club_agreement']}",
        f"- Backup-club agreement: {summary['backup_club_agreement']}",
        f"- Good-call rate: {summary['good_call_rate']}",
        f"- Directional hit rate: {summary['directional_hit_rate']}",
        "",
        "## Confidence Calibration",
        "- Confidence-to-success mapping used for Brier score: `high=0.85`, `medium=0.60`, `low=0.35`.",
        f"- Confidence calibration Brier score: {summary['confidence_calibration_brier']}",
        "",
        "## Confidence Buckets",
        "| Confidence | Runs | Predicted Success | Actual Success |",
        "|---|---:|---:|---:|",
    ]

    for bucket_name, bucket_summary in confidence_buckets.items():
        lines.append(
            "| "
            f"{bucket_name} | {bucket_summary['runs']} | {bucket_summary['predicted_success_probability']} | {bucket_summary['success_rate']} |"
        )

    lines.extend(["", "## Outcome Breakdown"])
    if outcome_breakdown:
        for outcome_name, count in outcome_breakdown.items():
            lines.append(f"- {outcome_name}: {count}")
    else:
        lines.append("- No linked feedback yet.")

    return "\n".join(lines)
