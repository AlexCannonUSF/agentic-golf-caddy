from datetime import datetime, timezone

from models import LieType, ShotEvent
from utils import build_profile_from_shots, build_tendencies, detect_import_format, import_shot_file


def test_detect_import_format() -> None:
    assert detect_import_format(["Player", "Club", "Carry", "Spin Rate"]) == "trackman"
    assert detect_import_format(["Player", "Club", "Carry Yards", "Backspin RPM"]) == "foresight"
    assert detect_import_format(["Player", "Club", "Shot Distance Yards", "Fairway Offset Ft"]) == "golfpad"


def test_build_tendencies_computes_confidence_dispersion_and_common_miss() -> None:
    shots = [
        ShotEvent(
            player_id="Test Player",
            club="7-iron",
            carry_yds=165,
            total_yds=170,
            offline_ft=20,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="7-iron",
            carry_yds=163,
            total_yds=168,
            offline_ft=18,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 12, 5, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="6-iron",
            carry_yds=176,
            total_yds=181,
            offline_ft=4,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 12, 10, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="6-iron",
            carry_yds=177,
            total_yds=182,
            offline_ft=-3,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 12, 15, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="5-iron",
            carry_yds=188,
            total_yds=193,
            offline_ft=10,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 12, 20, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="5-iron",
            carry_yds=190,
            total_yds=195,
            offline_ft=9,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 12, 25, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="4-hybrid",
            carry_yds=202,
            total_yds=209,
            offline_ft=5,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 12, 30, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="4-hybrid",
            carry_yds=203,
            total_yds=210,
            offline_ft=6,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 12, 35, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="8-iron",
            carry_yds=154,
            total_yds=158,
            offline_ft=7,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 12, 40, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="8-iron",
            carry_yds=153,
            total_yds=157,
            offline_ft=5,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 12, 45, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="9-iron",
            carry_yds=142,
            total_yds=146,
            offline_ft=4,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 12, 50, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="9-iron",
            carry_yds=141,
            total_yds=145,
            offline_ft=3,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 12, 55, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="pitching-wedge",
            carry_yds=129,
            total_yds=132,
            offline_ft=2,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 13, 0, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="pitching-wedge",
            carry_yds=128,
            total_yds=131,
            offline_ft=1,
            lie=LieType.FAIRWAY,
            source="manual",
            captured_at=datetime(2026, 4, 1, 13, 5, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="Driver",
            carry_yds=248,
            total_yds=269,
            offline_ft=14,
            lie=LieType.TEE,
            source="manual",
            captured_at=datetime(2026, 4, 1, 13, 10, tzinfo=timezone.utc),
        ),
        ShotEvent(
            player_id="Test Player",
            club="Driver",
            carry_yds=251,
            total_yds=272,
            offline_ft=12,
            lie=LieType.TEE,
            source="manual",
            captured_at=datetime(2026, 4, 1, 13, 15, tzinfo=timezone.utc),
        ),
    ]

    tendencies = build_tendencies(shots)
    profile = build_profile_from_shots(shots, profile_name="Test Player")

    assert tendencies.common_miss == "right"
    assert tendencies.confidence_by_club["6-iron"] >= 0.2
    assert tendencies.dispersion_by_club["7-iron"] > 0.0
    assert profile.preferred_shot.value in {"fade", "straight"}


def test_import_shot_file_detects_trackman_format_from_bytes() -> None:
    payload = (
        b"Player,Club,Carry,Total,Ball Speed,Spin Rate,Offline,Lie,Date Time\n"
        b"Alex Cannon,7-iron,180,184,120,6500,8,fairway,2026-04-01 12:00:00\n"
    )
    format_name, shots = import_shot_file(payload, source_name="trackman.csv")

    assert format_name == "trackman"
    assert len(shots) == 1
    assert shots[0].club == "7-iron"
