from engine.club_selector import select_clubs
from models import LieType, PlayerProfile, PlayerTendencies, ShotContext, SkillLevel, Strategy


def test_neutral_selects_closest(sample_profile) -> None:
    selection = select_clubs(150, sample_profile, Strategy.NEUTRAL)
    assert selection.primary_club == "6-iron"
    assert selection.backup_club == "7-iron"


def test_safe_biases_shorter_when_between_clubs(sample_profile) -> None:
    selection = select_clubs(150, sample_profile, Strategy.SAFE)
    assert selection.primary_club == "7-iron"
    assert selection.primary_distance == 145
    assert selection.backup_club == "6-iron"


def test_aggressive_biases_longer_when_between_clubs(sample_profile) -> None:
    selection = select_clubs(150, sample_profile, Strategy.AGGRESSIVE)
    assert selection.primary_club == "6-iron"
    assert selection.primary_distance == 155
    assert selection.backup_club == "7-iron"


def test_above_longest_uses_longest_with_backup(sample_profile) -> None:
    selection = select_clubs(260, sample_profile, Strategy.NEUTRAL)
    assert selection.primary_club == "Driver"
    assert selection.backup_club == "3-wood"


def test_below_shortest_uses_shortest_with_backup(sample_profile) -> None:
    selection = select_clubs(40, sample_profile, Strategy.NEUTRAL)
    assert selection.primary_club == "LW"
    assert selection.backup_club == "SW"


def test_bunker_guardrail_avoids_fairway_wood_on_borderline_shot() -> None:
    profile = PlayerProfile(
        name="Guardrail Player",
        skill_level=SkillLevel.INTERMEDIATE,
        club_distances={
            "Driver": 220,
            "3-wood": 180,
            "5-wood": 170,
            "4-hybrid": 165,
            "5-iron": 155,
            "6-iron": 145,
            "7-iron": 135,
            "8-iron": 125,
            "9-iron": 115,
            "PW": 105,
            "SW": 82,
            "LW": 62,
        },
    )

    context = ShotContext(distance_to_target=176, lie_type=LieType.BUNKER)
    selection = select_clubs(176, profile, Strategy.NEUTRAL, context)

    assert selection.primary_club in {"5-iron", "6-iron", "7-iron"}


def test_tendencies_break_near_ties_toward_more_trusted_club(sample_profile) -> None:
    trusted_profile = sample_profile.model_copy(
        deep=True,
        update={
            "tendencies": PlayerTendencies(
                confidence_by_club={"6-iron": 0.35, "7-iron": 0.95},
                dispersion_by_club={"6-iron": 22.0, "7-iron": 9.0},
            )
        },
    )

    context = ShotContext(distance_to_target=150.0)
    selection = select_clubs(150, trusted_profile, Strategy.NEUTRAL, context)

    assert selection.primary_club == "7-iron"


def test_intermediate_bunker_does_not_default_to_hybrid_or_wood(sample_profile) -> None:
    context = ShotContext(distance_to_target=165.0, lie_type=LieType.BUNKER)
    selection = select_clubs(175.0, sample_profile, Strategy.NEUTRAL, context)

    assert selection.primary_club in {"5-iron", "6-iron", "7-iron"}
