"""Unit tests for Agent 3: CoachAgent."""

from unittest.mock import MagicMock, patch

import pytest

from agents.coach_agent import CoachAgent, _format_adjustments, _template_fallback
from models import (
    AdaptiveDecision,
    CaddyDecision,
    ConfidenceLevel,
    Explanation,
    PlayerProfile,
    ShotContext,
    SkillLevel,
    Strategy,
)


@pytest.fixture
def decision(sample_profile: PlayerProfile) -> CaddyDecision:
    return CaddyDecision(
        primary_club="7-iron",
        backup_club="6-iron",
        plays_like_distance=160.0,
        actual_distance=150.0,
        adjustments={"wind": 5.0, "elevation": 5.0, "lie": 0.0, "temperature": 0.0, "altitude": 0.0},
        confidence=ConfidenceLevel.HIGH,
        strategy_note="Neutral pick: 7-iron (145 avg) is the closest match.",
    )


@pytest.fixture
def shot_context() -> ShotContext:
    return ShotContext(
        distance_to_target=150.0,
        wind_speed=5.0,
        elevation="uphill",
    )


class TestFormatAdjustments:
    def test_empty_adjustments(self) -> None:
        assert _format_adjustments({}) == "None"

    def test_all_zero(self) -> None:
        assert _format_adjustments({"wind": 0.0, "lie": 0.0}) == "None (all neutral)"

    def test_sorted_by_magnitude(self) -> None:
        result = _format_adjustments({"wind": 5.0, "elevation": 10.0, "lie": -3.0})
        parts = result.split(", ")
        assert "Elevation" in parts[0]
        assert len(parts) == 3


class TestTemplateFallback:
    def test_returns_explanation(
        self, decision: CaddyDecision, shot_context: ShotContext, sample_profile: PlayerProfile
    ) -> None:
        result = _template_fallback(decision, shot_context, sample_profile)
        assert isinstance(result, Explanation)
        assert "7-iron" in result.summary
        assert "150" in result.detail or "160" in result.detail
        assert result.backup_note  # non-empty

    def test_backup_note_suggests_longer_when_primary_short(
        self, shot_context: ShotContext, sample_profile: PlayerProfile
    ) -> None:
        decision = CaddyDecision(
            primary_club="7-iron",
            backup_club="6-iron",
            plays_like_distance=160.0,
            actual_distance=150.0,
            adjustments={"wind": 5.0, "elevation": 5.0},
            confidence=ConfidenceLevel.MEDIUM,
            strategy_note="test",
        )
        result = _template_fallback(decision, shot_context, sample_profile)
        assert decision.backup_club in result.backup_note

    def test_forced_layup_reads_clearly_in_fallback_copy(
        self, decision: CaddyDecision, shot_context: ShotContext, sample_profile: PlayerProfile
    ) -> None:
        bunker_context = shot_context.model_copy(update={"lie_type": "bunker"})
        adaptive = AdaptiveDecision(
            recommended_club="7-iron",
            target_line="layup window",
            strategy_rationale="Adaptive strategy shifted to a layup because the carry is not realistic.",
            risk_flags=["forced_layup", "carry_not_realistic"],
            used_history=False,
        )

        result = _template_fallback(decision, bunker_context, sample_profile, adaptive)

        assert result.summary == "Take a layup with your 7-iron."
        assert "controlled layup" in result.detail
        assert "aggressive fallback" in result.backup_note


class TestCoachAgentNoApiKey:
    def test_falls_back_to_template_without_api_key(
        self, decision: CaddyDecision, shot_context: ShotContext, sample_profile: PlayerProfile
    ) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
            agent = CoachAgent()
            result = agent.run(decision, shot_context, sample_profile)
        assert isinstance(result, Explanation)
        assert result.summary
        assert result.detail

    def test_falls_back_to_template_when_key_missing(
        self, decision: CaddyDecision, shot_context: ShotContext, sample_profile: PlayerProfile
    ) -> None:
        with patch.dict("os.environ", {}, clear=True):
            agent = CoachAgent()
            result = agent.run(decision, shot_context, sample_profile)
        assert isinstance(result, Explanation)


class TestCoachAgentWithMockedLLM:
    def test_uses_llm_when_api_key_present(
        self, decision: CaddyDecision, shot_context: ShotContext, sample_profile: PlayerProfile
    ) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = (
            "Go with your 7-iron. The 150-yard shot plays like 160 after headwind and uphill adjustments. "
            "If the wind picks up, bump to your 6-iron."
        )

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("agents.coach_agent.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                MockOpenAI.return_value = mock_client

                agent = CoachAgent()
                result = agent.run(decision, shot_context, sample_profile)

        assert isinstance(result, Explanation)
        assert "7-iron" in result.summary
        mock_client.chat.completions.create.assert_called_once()

    def test_falls_back_on_llm_exception(
        self, decision: CaddyDecision, shot_context: ShotContext, sample_profile: PlayerProfile
    ) -> None:
        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("agents.coach_agent.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                mock_client.chat.completions.create.side_effect = RuntimeError("API down")
                MockOpenAI.return_value = mock_client

                agent = CoachAgent()
                result = agent.run(decision, shot_context, sample_profile)

        assert isinstance(result, Explanation)
        assert result.summary  # should still produce fallback

    def test_falls_back_on_empty_llm_response(
        self, decision: CaddyDecision, shot_context: ShotContext, sample_profile: PlayerProfile
    ) -> None:
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = ""

        with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=False):
            with patch("agents.coach_agent.OpenAI") as MockOpenAI:
                mock_client = MagicMock()
                mock_client.chat.completions.create.return_value = mock_response
                MockOpenAI.return_value = mock_client

                agent = CoachAgent()
                result = agent.run(decision, shot_context, sample_profile)

        assert isinstance(result, Explanation)
        assert result.summary
