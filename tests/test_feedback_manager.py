from models import PlayerProfile, ShotFeedback, ShotOutcome, SkillLevel
from utils.feedback_manager import FeedbackManager


def _profile() -> PlayerProfile:
    return PlayerProfile(
        name="Feedback Player",
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


def test_feedback_manager_summarizes_player_tendencies(tmp_path) -> None:
    manager = FeedbackManager(tmp_path / "feedback.json")
    profile = _profile()

    manager.add_feedback(profile.name, ShotFeedback(club_used="7-iron", outcome=ShotOutcome.SHORT))
    manager.add_feedback(profile.name, ShotFeedback(club_used="7-iron", outcome=ShotOutcome.SHORT))
    manager.add_feedback(profile.name, ShotFeedback(club_used="6-iron", outcome=ShotOutcome.ON_TARGET))

    summary = manager.summarize_tendencies(profile)

    assert summary.common_miss == "short"
    assert summary.confidence_by_club["7-iron"] < summary.confidence_by_club["6-iron"]
    assert summary.dispersion_by_club["7-iron"] > summary.dispersion_by_club["6-iron"]
    assert len(manager.load_all_feedback()) == 3
