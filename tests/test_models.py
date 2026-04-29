# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
import pytest
from pydantic import ValidationError

from models import CaddyDecision, ConfidenceLevel, Explanation, PlayerProfile, ShotContext


def test_shot_context_accepts_valid_payload(sample_valid_shot_input: dict[str, object]) -> None:
    context = ShotContext.model_validate(sample_valid_shot_input)

    assert context.distance_to_target == 150.0
    assert context.wind_speed == 10.0
    assert context.lie_type.value == "fairway"
    assert context.strategy.value == "neutral"


def test_shot_context_accepts_optional_pin_coordinates(sample_valid_shot_input: dict[str, object]) -> None:
    payload = dict(sample_valid_shot_input)
    payload["origin_lat_lon"] = {"lat": 40.0, "lon": -73.0}
    payload["pin_lat_lon"] = {"lat": 40.0005, "lon": -73.001}

    context = ShotContext.model_validate(payload)

    assert context.origin_lat_lon is not None
    assert context.pin_lat_lon is not None


def test_shot_context_rejects_out_of_range_distance(sample_valid_shot_input: dict[str, object]) -> None:
    invalid_payload = dict(sample_valid_shot_input)
    invalid_payload["distance_to_target"] = 20

    with pytest.raises(ValidationError):
        ShotContext.model_validate(invalid_payload)


def test_player_profile_requires_descending_standard_bag(
    sample_profile: PlayerProfile,
) -> None:
    invalid_distances = dict(sample_profile.club_distances)
    invalid_distances["8-iron"] = invalid_distances["7-iron"] + 1

    with pytest.raises(ValidationError):
        PlayerProfile(
            name=sample_profile.name,
            skill_level=sample_profile.skill_level,
            club_distances=invalid_distances,
            preferred_shot=sample_profile.preferred_shot,
        )


def test_caddy_decision_requires_different_primary_and_backup() -> None:
    with pytest.raises(ValidationError):
        CaddyDecision(
            primary_club="7-iron",
            backup_club="7-iron",
            plays_like_distance=170,
            actual_distance=150,
            adjustments={"wind": 10, "elevation": 10},
            confidence=ConfidenceLevel.MEDIUM,
            strategy_note="Neutral pick.",
        )


def test_explanation_requires_non_empty_fields() -> None:
    with pytest.raises(ValidationError):
        Explanation(summary="", detail="x", adjustment_breakdown="x", backup_note="x")
