import pytest

from models import SkillLevel
from utils.profile_manager import ProfileAlreadyExistsError


def test_create_and_load_profile(profile_manager, sample_profile) -> None:
    saved_path = profile_manager.create_profile(sample_profile)

    assert saved_path.exists()
    assert saved_path.name == "alex_cannon.json"

    loaded = profile_manager.load_profile("alex_cannon")
    assert loaded == sample_profile


def test_create_profile_raises_if_already_exists(profile_manager, sample_profile) -> None:
    profile_manager.create_profile(sample_profile)

    with pytest.raises(ProfileAlreadyExistsError):
        profile_manager.create_profile(sample_profile)


def test_update_profile_can_rename(profile_manager, sample_profile) -> None:
    profile_manager.create_profile(sample_profile)

    updated = profile_manager.update_profile(
        "alex_cannon",
        name="Alex Pro",
        skill_level="advanced",
    )

    assert updated.name == "Alex Pro"
    assert updated.skill_level == SkillLevel.ADVANCED
    assert "alex_pro" in profile_manager.list_profiles()
    assert "alex_cannon" not in profile_manager.list_profiles()


def test_delete_profile(profile_manager, sample_profile) -> None:
    profile_manager.create_profile(sample_profile)

    profile_manager.delete_profile("alex_cannon")

    assert "alex_cannon" not in profile_manager.list_profiles()


def test_load_default_profile(profile_manager) -> None:
    beginner = profile_manager.load_default_profile("beginner")

    assert beginner.skill_level == SkillLevel.BEGINNER
    assert beginner.club_distances["Driver"] == 190.0
