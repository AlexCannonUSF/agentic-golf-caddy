from pathlib import Path

from utils import build_profile_from_shots, import_golfpad_csv


def _fixture_path(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "imports" / name


def test_golfpad_importer_parses_round_export() -> None:
    shots = import_golfpad_csv(
        _fixture_path("golfpad_round_export.csv").read_bytes(),
        source_name="golfpad_round_export.csv",
    )

    assert len(shots) == 12
    assert shots[0].source == "golfpad"
    assert shots[0].club == "Driver"
    assert shots[-1].club == "SW"
    assert shots[-1].lie.value == "bunker"


def test_golfpad_import_produces_profile_with_enough_clubs() -> None:
    profile = build_profile_from_shots(
        import_golfpad_csv(
            _fixture_path("golfpad_round_export.csv").read_bytes(),
            source_name="golfpad_round_export.csv",
        )
    )

    assert profile.name == "Morgan Golfer"
    assert len(profile.club_distances) >= 8

