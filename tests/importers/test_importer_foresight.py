# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
from pathlib import Path

from utils import build_profile_from_shots, import_foresight_csv


def _fixture_path(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "imports" / name


def test_foresight_importer_parses_expected_fields() -> None:
    shots = import_foresight_csv(
        _fixture_path("foresight_fsx_export.csv").read_bytes(),
        source_name="foresight_fsx_export.csv",
    )

    assert len(shots) == 12
    assert shots[0].source == "foresight"
    assert shots[0].club == "Driver"
    assert shots[2].spin_rpm == 5600.0
    assert shots[6].lie.value == "rough"


def test_foresight_import_produces_reasonable_profile() -> None:
    profile = build_profile_from_shots(
        import_foresight_csv(
            _fixture_path("foresight_fsx_export.csv").read_bytes(),
            source_name="foresight_fsx_export.csv",
        )
    )

    assert profile.name == "Jamie Player"
    assert profile.club_distances["Driver"] >= 239.0

