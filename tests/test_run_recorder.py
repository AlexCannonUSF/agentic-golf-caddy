# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
import json

from agents.pipeline import Pipeline
from evaluation.real_runs import render_real_run_report, summarize_real_runs
from models import (
    CaddyDecision,
    ConfidenceLevel,
    Explanation,
    RecommendationRating,
    ShotContext,
    ShotFeedback,
    ShotOutcome,
)
from scripts.evaluate_runs import build_report
from utils.evaluation import RunRecorder
from utils.feedback_manager import FeedbackManager


def _decision() -> CaddyDecision:
    return CaddyDecision(
        primary_club="7-iron",
        backup_club="6-iron",
        plays_like_distance=152.0,
        actual_distance=150.0,
        adjustments={"wind": 2.0, "elevation": 0.0, "lie": 0.0, "temperature": 0.0, "altitude": 0.0},
        confidence=ConfidenceLevel.HIGH,
        strategy_note="7-iron is the clean stock number.",
    )


def _explanation() -> Explanation:
    return Explanation(
        summary="Hit 7-iron.",
        detail="The shot is a stock 7-iron number.",
        adjustment_breakdown="Wind adds a couple yards.",
        backup_note="6-iron is the safer longer miss.",
    )


def test_run_recorder_hydrates_feedback_and_latency(tmp_path, sample_profile) -> None:
    runs_file = tmp_path / "runs.jsonl"
    feedback_file = tmp_path / "feedback.json"
    recorder = RunRecorder(runs_file)
    feedback_manager = FeedbackManager(feedback_file)

    run_id = recorder.new_run_id()
    recorder.record_pipeline_result(
        run_id=run_id,
        raw_input={"distance_to_target": 150},
        player_profile=sample_profile,
        shot_context=ShotContext(distance_to_target=150.0),
        decision=_decision(),
        explanation=_explanation(),
        timing_seconds={"total": 0.123},
    )
    feedback_manager.add_feedback(
        sample_profile.name,
        ShotFeedback(
            run_id=run_id,
            club_used="7-iron",
            outcome=ShotOutcome.ON_TARGET,
            recommendation_rating=RecommendationRating.GOOD_CALL,
        ),
    )

    records = recorder.load_records(feedback_file=feedback_file)

    assert len(records) == 1
    assert records[0].outcome is not None
    assert records[0].outcome.run_id == run_id
    assert records[0].latency_ms["total"] == 123.0


def test_run_recorder_exports_promotable_real_shots(tmp_path, sample_profile) -> None:
    runs_file = tmp_path / "runs.jsonl"
    feedback_file = tmp_path / "feedback.json"
    export_file = tmp_path / "real_shots.json"
    recorder = RunRecorder(runs_file)
    feedback_manager = FeedbackManager(feedback_file)

    run_id = recorder.new_run_id()
    recorder.record_pipeline_result(
        run_id=run_id,
        raw_input={"distance_to_target": 150, "wind_speed": 8},
        player_profile=sample_profile,
        shot_context=ShotContext(distance_to_target=150.0),
        decision=_decision(),
        explanation=_explanation(),
        timing_seconds={"total": 0.2},
    )
    feedback_manager.add_feedback(
        sample_profile.name,
        ShotFeedback(
            run_id=run_id,
            club_used="7-iron",
            outcome=ShotOutcome.GOOD_CONTACT,
            recommendation_rating=RecommendationRating.GOOD_CALL,
        ),
    )

    path = recorder.export_promoted_benchmarks(output_path=export_file, feedback_file=feedback_file)
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert path == export_file
    assert payload[0]["case_id"] == run_id
    assert payload[0]["expected_club"] == "7-iron"
    assert "7-iron" in payload[0]["acceptable_clubs"]


def test_pipeline_records_real_run_with_run_id(tmp_path, sample_profile) -> None:
    recorder = RunRecorder(tmp_path / "runs.jsonl")
    pipeline = Pipeline(sample_profile)
    pipeline._run_recorder = recorder

    result = pipeline.run({"distance_to_target": 150})
    records = recorder.load_records()

    assert result.run_id is not None
    assert len(records) == 1
    assert records[0].run_id == result.run_id
    assert records[0].decision is not None
    assert records[0].explanation_summary


def test_real_run_summary_and_script_report(tmp_path, sample_profile) -> None:
    runs_file = tmp_path / "runs.jsonl"
    feedback_file = tmp_path / "feedback.json"
    recorder = RunRecorder(runs_file)
    feedback_manager = FeedbackManager(feedback_file)

    run_id = recorder.new_run_id()
    recorder.record_pipeline_result(
        run_id=run_id,
        raw_input={"distance_to_target": 150},
        player_profile=sample_profile,
        shot_context=ShotContext(distance_to_target=150.0),
        decision=_decision(),
        explanation=_explanation(),
        timing_seconds={"total": 0.15},
    )
    feedback_manager.add_feedback(
        sample_profile.name,
        ShotFeedback(
            run_id=run_id,
            club_used="7-iron",
            outcome=ShotOutcome.ON_TARGET,
            recommendation_rating=RecommendationRating.GOOD_CALL,
        ),
    )

    records = recorder.load_records(feedback_file=feedback_file)
    summary = summarize_real_runs(records)
    markdown = render_real_run_report(summary)
    script_report = build_report(runs_file=runs_file, feedback_file=feedback_file)

    assert summary["primary_club_agreement"] == 1.0
    assert summary["confidence_calibration_brier"] >= 0.0
    assert "# Real Run Evaluation Report" in markdown
    assert "Primary-club agreement" in script_report
