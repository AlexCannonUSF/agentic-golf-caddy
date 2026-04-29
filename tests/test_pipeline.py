# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Integration tests for the full 3-agent pipeline."""

import json
from unittest.mock import MagicMock, patch
from pathlib import Path

import pytest

from agents.context_agent import ContextAgent
from agents.pipeline import Pipeline, PipelineResult
from models import (
    CaddyDecision,
    ConfidenceLevel,
    Explanation,
    PlayerProfile,
    ShotFeedback,
    ShotOutcome,
    ShotContext,
    SkillLevel,
)
from utils.course_manager import CourseManager
from utils.data_sources.osm_parser import parse_course_payload
from utils.feedback_manager import FeedbackManager
from utils.validators import InputValidationError


@pytest.fixture
def pipeline(sample_profile: PlayerProfile) -> Pipeline:
    return Pipeline(sample_profile)


@pytest.fixture
def debug_pipeline(sample_profile: PlayerProfile) -> Pipeline:
    return Pipeline(sample_profile, debug=True)


class TestPipelineEndToEnd:
    """Full pipeline: raw input → ShotContext → CaddyDecision → Explanation."""

    def test_basic_shot_produces_complete_result(self, pipeline: Pipeline) -> None:
        result = pipeline.run({"distance_to_target": 150})
        assert isinstance(result, PipelineResult)
        assert isinstance(result.shot_context, ShotContext)
        assert isinstance(result.decision, CaddyDecision)
        assert isinstance(result.explanation, Explanation)

    def test_timing_data_present(self, pipeline: Pipeline) -> None:
        result = pipeline.run({"distance_to_target": 150})
        assert "context_agent" in result.timing
        assert "decision_agent" in result.timing
        assert "coach_agent" in result.timing
        assert "total" in result.timing
        assert all(t >= 0 for t in result.timing.values())

    def test_pipeline_with_all_conditions(self, pipeline: Pipeline) -> None:
        result = pipeline.run({
            "distance_to_target": 160,
            "lie_type": "rough",
            "wind_speed": 15,
            "wind_direction": "headwind",
            "elevation": "uphill",
            "strategy": "aggressive",
            "temperature": 50,
            "altitude_ft": 5000,
        })
        assert result.decision.plays_like_distance > result.decision.actual_distance
        assert result.decision.primary_club != result.decision.backup_club
        assert result.explanation.summary

    def test_pipeline_with_aliases(self, pipeline: Pipeline) -> None:
        result = pipeline.run({
            "distance_to_target": 150,
            "lie_type": "tee_box",
            "wind_direction": "into",
            "strategy": "conservative",
        })
        assert result.shot_context.lie_type.value == "tee"
        assert result.shot_context.wind_direction.value == "headwind"
        assert result.shot_context.strategy.value == "safe"


class TestPipelineErrorHandling:
    def test_invalid_input_raises_validation_error(self, pipeline: Pipeline) -> None:
        with pytest.raises(InputValidationError):
            pipeline.run({"distance_to_target": "not_a_number"})

    def test_missing_distance_raises_validation_error(self, pipeline: Pipeline) -> None:
        with pytest.raises(InputValidationError):
            pipeline.run({"lie_type": "fairway"})

    def test_distance_too_low_raises(self, pipeline: Pipeline) -> None:
        with pytest.raises(InputValidationError):
            pipeline.run({"distance_to_target": 5})

    def test_distance_too_high_raises(self, pipeline: Pipeline) -> None:
        with pytest.raises(InputValidationError):
            pipeline.run({"distance_to_target": 500})


class TestPipelineWithMockedLLM:
    def test_pipeline_with_mocked_openai(self, sample_profile: PlayerProfile) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            "Go with your 6-iron for this 150-yard approach. "
            "It plays a bit longer with the wind, but your 6-iron is a solid pick."
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("agents.coach_agent.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                MockOpenAI.return_value = mock_client

                pipeline = Pipeline(sample_profile)
                result = pipeline.run({"distance_to_target": 150})

        assert isinstance(result.explanation, Explanation)
        assert "6-iron" in result.explanation.summary
        mock_client.chat.completions.create.assert_called_once()

    def test_pipeline_survives_llm_failure(self, sample_profile: PlayerProfile) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("agents.coach_agent.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                mock_client.chat.completions.create.side_effect = RuntimeError("Network error")
                MockOpenAI.return_value = mock_client

                pipeline = Pipeline(sample_profile)
                result = pipeline.run({"distance_to_target": 150})

        assert isinstance(result.explanation, Explanation)
        assert result.explanation.summary


class TestPipelineDebugMode:
    def test_debug_mode_does_not_error(self, debug_pipeline: Pipeline) -> None:
        result = debug_pipeline.run({"distance_to_target": 150})
        assert isinstance(result, PipelineResult)

    def test_non_debug_mode_also_works(self, pipeline: Pipeline) -> None:
        result = pipeline.run({"distance_to_target": 150})
        assert isinstance(result, PipelineResult)


class TestPipelineStrategyVariations:
    """Same conditions, different strategies should produce different clubs."""

    @pytest.fixture
    def base_input(self) -> dict:
        return {
            "distance_to_target": 150,
            "lie_type": "fairway",
            "wind_speed": 0,
            "elevation": "flat",
        }

    def test_safe_vs_aggressive_different_clubs(
        self, sample_profile: PlayerProfile, base_input: dict
    ) -> None:
        safe_input = {**base_input, "strategy": "safe"}
        aggressive_input = {**base_input, "strategy": "aggressive"}

        safe_pipe = Pipeline(sample_profile)
        aggressive_pipe = Pipeline(sample_profile)

        safe_result = safe_pipe.run(safe_input)
        agg_result = aggressive_pipe.run(aggressive_input)

        safe_dist = sample_profile.club_distances[safe_result.decision.primary_club]
        agg_dist = sample_profile.club_distances[agg_result.decision.primary_club]
        assert safe_dist <= agg_dist


class TestPipelineProfileVariations:
    """Same shot with different profiles should give different clubs."""

    def test_beginner_vs_advanced_different_clubs(
        self, profile_manager, default_profiles_dir
    ) -> None:
        from utils.profile_manager import ProfileManager

        pm = ProfileManager(default_profiles_dir=default_profiles_dir)
        beginner = pm.load_default_profile("beginner")
        advanced = pm.load_default_profile("advanced")

        raw = {"distance_to_target": 180, "strategy": "neutral"}

        beg_result = Pipeline(beginner).run(raw)
        adv_result = Pipeline(advanced).run(raw)

        assert beg_result.decision.primary_club != adv_result.decision.primary_club

    def test_feedback_history_can_personalize_borderline_club_choice(
        self, tmp_path, sample_profile: PlayerProfile
    ) -> None:
        manager = FeedbackManager(tmp_path / "feedback.json")
        manager.add_feedback(sample_profile.name, ShotFeedback(club_used="6-iron", outcome=ShotOutcome.SHORT))
        manager.add_feedback(sample_profile.name, ShotFeedback(club_used="6-iron", outcome=ShotOutcome.SHORT))
        manager.add_feedback(sample_profile.name, ShotFeedback(club_used="7-iron", outcome=ShotOutcome.ON_TARGET))
        manager.add_feedback(sample_profile.name, ShotFeedback(club_used="7-iron", outcome=ShotOutcome.ON_TARGET))

        pipeline = Pipeline(sample_profile)
        pipeline._feedback_manager = manager

        result = pipeline.run({"distance_to_target": 150.0})

        assert result.decision is not None
        assert result.decision.primary_club == "7-iron"

    def test_pipeline_forces_layup_on_unrealistic_deep_rough_carry(
        self, sample_profile: PlayerProfile
    ) -> None:
        result = Pipeline(sample_profile).run(
            {"distance_to_target": 220.0, "lie_type": "deep_rough", "strategy": "aggressive"}
        )

        assert result.adaptive_decision is not None
        assert result.decision is not None
        assert result.adaptive_decision.target_line == "layup window"
        assert "forced_layup" in result.adaptive_decision.risk_flags
        assert result.decision.primary_club in {"4-hybrid", "5-iron", "6-iron"}
        assert result.explanation is not None
        assert "layup" in result.explanation.summary.lower()


class TestPipelineScenarioMatrix:
    """Diverse scenarios testing the full pipeline for correctness."""

    SCENARIOS = [
        {"distance_to_target": 100, "lie_type": "fairway"},
        {"distance_to_target": 200, "lie_type": "tee", "wind_speed": 20, "wind_direction": "headwind"},
        {"distance_to_target": 150, "lie_type": "rough", "elevation": "steep_uphill"},
        {"distance_to_target": 75, "lie_type": "bunker", "strategy": "safe"},
        {"distance_to_target": 250, "lie_type": "fairway", "wind_speed": 10, "wind_direction": "tailwind"},
        {"distance_to_target": 130, "temperature": 45, "altitude_ft": 5000},
        {"distance_to_target": 160, "lie_type": "deep_rough", "wind_speed": 25, "wind_direction": "crosswind_left"},
        {"distance_to_target": 180, "elevation": "steep_downhill", "strategy": "aggressive"},
    ]

    @pytest.mark.parametrize("raw_input", SCENARIOS, ids=[
        "100yd_fairway",
        "200yd_tee_headwind20",
        "150yd_rough_steep_uphill",
        "75yd_bunker_safe",
        "250yd_fairway_tailwind10",
        "130yd_cold_highalt",
        "160yd_deep_rough_crosswind25",
        "180yd_steep_down_aggressive",
    ])
    def test_scenario_completes_successfully(self, pipeline: Pipeline, raw_input: dict) -> None:
        result = pipeline.run(raw_input)
        assert isinstance(result, PipelineResult)
        assert result.decision.primary_club
        assert result.decision.backup_club
        assert result.explanation.summary
        assert result.decision.plays_like_distance > 0


class TestPipelineCourseContextSafety:
    def test_text_distance_is_preserved_even_with_selected_course(self, tmp_path, sample_profile) -> None:
        fixture_path = Path(__file__).resolve().parent / "fixtures" / "data_sources" / "overpass_torrey_south.json"
        course_payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        course = parse_course_payload(course_payload, course_id="torrey_pines_south", osm_ref="way/35679036")

        course_manager = CourseManager(tmp_path / "courses")
        course_manager.save_course(course)

        pipeline = Pipeline(sample_profile)
        pipeline._context_agent = ContextAgent(course_manager=course_manager)

        result = pipeline.run(
            {
                "shot_text": "I am in a fairway bunker 130 yards in",
                "course_id": "torrey_pines_south",
                "hole_number": 3,
                "pin_source": "front",
            }
        )

        assert result.shot_context is not None
        assert result.decision is not None
        assert result.shot_context.distance_to_target == 130.0
        assert result.decision.actual_distance == 130.0
        assert result.decision.primary_club != "Driver"
