# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Unit tests for Agent 2: DecisionAgent."""

import pytest

from agents.decision_agent import DecisionAgent
from models import (
    CaddyDecision,
    ConfidenceLevel,
    Elevation,
    LieType,
    LatLon,
    PlayerProfile,
    ShotContext,
    SkillLevel,
    Strategy,
    WindDirection,
)


@pytest.fixture
def agent() -> DecisionAgent:
    return DecisionAgent()


@pytest.fixture
def baseline_context() -> ShotContext:
    return ShotContext(distance_to_target=150.0)


@pytest.fixture
def complex_context() -> ShotContext:
    return ShotContext(
        distance_to_target=150.0,
        lie_type=LieType.ROUGH,
        wind_speed=15.0,
        wind_direction=WindDirection.HEADWIND,
        elevation=Elevation.UPHILL,
        strategy=Strategy.NEUTRAL,
    )


class TestDecisionAgentOutput:
    def test_returns_caddy_decision(
        self, agent: DecisionAgent, baseline_context: ShotContext, sample_profile: PlayerProfile
    ) -> None:
        result = agent.run(baseline_context, sample_profile)
        assert isinstance(result, CaddyDecision)

    def test_primary_and_backup_differ(
        self, agent: DecisionAgent, baseline_context: ShotContext, sample_profile: PlayerProfile
    ) -> None:
        result = agent.run(baseline_context, sample_profile)
        assert result.primary_club != result.backup_club

    def test_actual_distance_matches_input(
        self, agent: DecisionAgent, baseline_context: ShotContext, sample_profile: PlayerProfile
    ) -> None:
        result = agent.run(baseline_context, sample_profile)
        assert result.actual_distance == 150.0

    def test_actual_distance_uses_pin_coordinates_when_available(
        self, agent: DecisionAgent, sample_profile: PlayerProfile
    ) -> None:
        context = ShotContext(
            distance_to_target=150.0,
            origin_lat_lon=LatLon(lat=40.0, lon=-73.0),
            pin_lat_lon=LatLon(lat=40.0005, lon=-73.001),
        )
        result = agent.run(context, sample_profile)

        assert result.actual_distance != 150.0

    def test_plays_like_equals_actual_for_neutral_conditions(
        self, agent: DecisionAgent, sample_profile: PlayerProfile
    ) -> None:
        ctx = ShotContext(distance_to_target=150.0)
        result = agent.run(ctx, sample_profile)
        assert result.plays_like_distance == 150.0

    def test_adjustments_populated_with_conditions(
        self, agent: DecisionAgent, complex_context: ShotContext, sample_profile: PlayerProfile
    ) -> None:
        result = agent.run(complex_context, sample_profile)
        assert "wind" in result.adjustments
        assert "elevation" in result.adjustments
        assert "lie" in result.adjustments
        assert result.plays_like_distance > result.actual_distance


class TestDecisionAgentStrategies:
    def test_safe_strategy_selects_shorter_club(
        self, agent: DecisionAgent, sample_profile: PlayerProfile
    ) -> None:
        ctx = ShotContext(distance_to_target=150.0, strategy=Strategy.SAFE)
        result = agent.run(ctx, sample_profile)
        club_dist = sample_profile.club_distances[result.primary_club]
        assert club_dist <= 150.0

    def test_aggressive_strategy_selects_longer_club(
        self, agent: DecisionAgent, sample_profile: PlayerProfile
    ) -> None:
        ctx = ShotContext(distance_to_target=150.0, strategy=Strategy.AGGRESSIVE)
        result = agent.run(ctx, sample_profile)
        club_dist = sample_profile.club_distances[result.primary_club]
        assert club_dist >= 150.0


class TestDecisionAgentConfidence:
    def test_high_confidence_for_close_match(
        self, agent: DecisionAgent, sample_profile: PlayerProfile
    ) -> None:
        ctx = ShotContext(distance_to_target=155.0)
        result = agent.run(ctx, sample_profile)
        assert result.confidence == ConfidenceLevel.HIGH

    def test_confidence_degrades_for_extreme_wind(
        self, agent: DecisionAgent, sample_profile: PlayerProfile
    ) -> None:
        ctx = ShotContext(distance_to_target=150.0, wind_speed=35.0, wind_direction=WindDirection.HEADWIND)
        result = agent.run(ctx, sample_profile)
        assert result.confidence in {ConfidenceLevel.MEDIUM, ConfidenceLevel.LOW}

    def test_confidence_degrades_when_player_feels_uncomfortable(
        self, agent: DecisionAgent, sample_profile: PlayerProfile
    ) -> None:
        ctx = ShotContext(distance_to_target=155.0, player_confidence=1)
        result = agent.run(ctx, sample_profile)
        assert result.confidence == ConfidenceLevel.MEDIUM
