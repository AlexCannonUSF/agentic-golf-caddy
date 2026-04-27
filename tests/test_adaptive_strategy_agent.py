from unittest.mock import patch

from agents.adaptive_strategy_agent import AdaptiveStrategyAgent
from models import CandidateOption, PlayerTendencies, ShotContext


def test_adaptive_strategy_agent_re_ranks_with_hazard_and_low_confidence() -> None:
    agent = AdaptiveStrategyAgent()
    shot_context = ShotContext.model_validate(
        {
            "distance_to_target": 150,
            "target_mode": "center_green",
            "hazard_note": "bunker_long",
            "player_confidence": 2,
        }
    )
    candidate_options = [
        CandidateOption(club_name="6-iron", club_distance=155, distance_gap=5),
        CandidateOption(club_name="7-iron", club_distance=145, distance_gap=5),
        CandidateOption(club_name="5-iron", club_distance=165, distance_gap=15),
    ]
    tendencies = PlayerTendencies(
        common_miss="short",
        confidence_by_club={"6-iron": 0.9, "7-iron": 0.5},
        dispersion_by_club={"6-iron": 6.0, "7-iron": 12.0},
    )

    with patch.object(agent, "_llm_strategy", side_effect=RuntimeError("No API")):
        result = agent.run(shot_context, candidate_options, tendencies)

    assert result.recommended_club == "7-iron"
    assert result.target_line == "center green"
    assert "long_side_penalty" in result.risk_flags
    assert "low_player_confidence" in result.risk_flags


def test_adaptive_strategy_agent_respects_bunker_guardrails() -> None:
    agent = AdaptiveStrategyAgent()
    shot_context = ShotContext.model_validate(
        {
            "distance_to_target": 165,
            "lie_type": "bunker",
        }
    )
    candidate_options = [
        CandidateOption(club_name="3-wood", club_distance=175, distance_gap=0),
        CandidateOption(club_name="4-hybrid", club_distance=150, distance_gap=15),
        CandidateOption(club_name="6-iron", club_distance=130, distance_gap=35),
    ]
    tendencies = PlayerTendencies()

    with patch.object(agent, "_llm_strategy", side_effect=RuntimeError("No API")):
        result = agent.run(shot_context, candidate_options, tendencies)

    assert result.recommended_club == "6-iron"
    assert set(result.risk_flags) & {"guardrail_override", "forced_layup"}


def test_adaptive_strategy_agent_forces_layup_when_carry_is_not_realistic() -> None:
    agent = AdaptiveStrategyAgent()
    shot_context = ShotContext.model_validate(
        {
            "distance_to_target": 220,
            "lie_type": "deep_rough",
        }
    )
    candidate_options = [
        CandidateOption(club_name="3-wood", club_distance=205, distance_gap=15),
        CandidateOption(club_name="4-hybrid", club_distance=185, distance_gap=35),
        CandidateOption(club_name="5-iron", club_distance=170, distance_gap=50),
        CandidateOption(club_name="6-iron", club_distance=160, distance_gap=60),
    ]
    tendencies = PlayerTendencies()

    with patch.object(agent, "_llm_strategy", side_effect=AssertionError("LLM path should be bypassed")):
        result = agent.run(shot_context, candidate_options, tendencies)

    assert result.recommended_club == "4-hybrid"
    assert result.target_line == "layup window"
    assert "forced_layup" in result.risk_flags
    assert "carry_not_realistic" in result.risk_flags
