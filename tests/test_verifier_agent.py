from agents.verifier_agent import VerifierAgent
from models import Explanation, PlayerProfile, SkillLevel


def _profile() -> PlayerProfile:
    return PlayerProfile(
        name="Verifier Player",
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


def test_verifier_allows_club_name_digits_and_adjustment_values() -> None:
    explanation = Explanation(
        summary="Use your 3-wood.",
        detail="The shot plays 200 yards after a 5-yard wind adjustment.",
        adjustment_breakdown="Wind: +5.0 yds",
        backup_note="Backup: 5-wood (185 avg) if conditions change.",
    )

    result = VerifierAgent().run(
        explanation,
        _profile(),
        primary_club="3-wood",
        backup_club="5-wood",
        actual_distance=195,
        plays_like_distance=200,
        adjustments={"wind": 5.0},
    )

    assert result.is_grounded is True
    assert result.issues == []


def test_verifier_flags_invented_club_and_number() -> None:
    explanation = Explanation(
        summary="Use your 8-iron.",
        detail="It plays 167 yards today.",
        adjustment_breakdown="Wind: +7.0 yds",
        backup_note="Backup: 7-iron.",
    )

    result = VerifierAgent().run(
        explanation,
        _profile(),
        primary_club="6-iron",
        backup_club="7-iron",
        actual_distance=150,
        plays_like_distance=155,
        adjustments={"wind": 5.0},
    )

    assert result.is_grounded is False
    assert any("unsupported clubs" in issue for issue in result.issues)
    assert any("unsupported number" in issue for issue in result.issues)

