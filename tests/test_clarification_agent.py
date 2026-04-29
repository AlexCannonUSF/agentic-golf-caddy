# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
from agents.clarification_agent import ClarificationAgent
from models import CourseContext, PlayerProfile, ShotIntent, SkillLevel, UserIntent


def _sample_profile() -> PlayerProfile:
    return PlayerProfile(
        name="Test Player",
        skill_level=SkillLevel.INTERMEDIATE,
        club_distances={
            "Driver": 220,
            "3-wood": 200,
            "5-wood": 185,
            "4-hybrid": 175,
            "5-iron": 165,
            "6-iron": 155,
            "7-iron": 145,
            "8-iron": 135,
            "9-iron": 125,
            "PW": 115,
            "SW": 80,
            "LW": 60,
        },
    )


def test_clarification_agent_asks_for_missing_distance() -> None:
    agent = ClarificationAgent()
    intent = ShotIntent(
        raw_text="Into the wind a little, rough lie, back pin.",
        parsed_fields={"wind_direction": "headwind", "lie_type": "rough"},
        field_confidence={"wind_direction": 0.9, "lie_type": 0.9},
        missing_fields=["distance_to_target"],
        ambiguous_fields=[],
        course_context=CourseContext(),
        user_intent=UserIntent(),
    )

    result = agent.run(intent, _sample_profile())

    assert result.needs_clarification is True
    assert "yards" in (result.question or "").lower()
    assert result.decision_sensitivity == 1.0


def test_clarification_agent_skips_structured_input() -> None:
    agent = ClarificationAgent()
    intent = ShotIntent(
        raw_text="[structured_input]",
        parsed_fields={"distance_to_target": 150},
        field_confidence={"distance_to_target": 1.0},
        missing_fields=[],
        ambiguous_fields=[],
        course_context=CourseContext(),
        user_intent=UserIntent(),
    )

    result = agent.run(intent, _sample_profile())

    assert result.needs_clarification is False
    assert result.question is None

