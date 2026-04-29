# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
import pytest

from models import STANDARD_BAG_ORDER, SkillLevel
from utils.wizard import build_profile_from_quick_calibration, interpolate_club_distances


def test_interpolate_club_distances_returns_full_standard_bag() -> None:
    distances = interpolate_club_distances(220, 145, 115)

    assert list(distances.keys()) == list(STANDARD_BAG_ORDER)
    assert distances["Driver"] == 220.0
    assert distances["7-iron"] == 145.0
    assert distances["PW"] == 115.0


def test_interpolated_distances_are_strictly_descending() -> None:
    distances = interpolate_club_distances(250, 165, 130)
    values = [distances[club] for club in STANDARD_BAG_ORDER]

    assert all(values[idx] > values[idx + 1] for idx in range(len(values) - 1))


def test_interpolate_club_distances_rejects_invalid_anchor_order() -> None:
    with pytest.raises(ValueError, match="Driver > 7-iron > PW"):
        interpolate_club_distances(170, 175, 120)


def test_build_profile_from_quick_calibration_creates_valid_profile() -> None:
    profile = build_profile_from_quick_calibration(
        name="Quick Start",
        skill_level=SkillLevel.INTERMEDIATE,
        driver_distance=220,
        seven_iron_distance=145,
        pitching_wedge_distance=115,
    )

    assert profile.name == "Quick Start"
    assert profile.skill_level == SkillLevel.INTERMEDIATE
    assert profile.club_distances["Driver"] == 220.0
    assert profile.club_distances["PW"] == 115.0
