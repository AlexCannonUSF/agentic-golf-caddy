# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
from pathlib import Path

from agents.pipeline import Pipeline
from models import PlayerProfile, ShotEvent
from utils import build_profile_from_shots, import_trackman_csv, load_shots, save_shots


def _fixture_path(name: str) -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / "imports" / name


def test_trackman_importer_parses_200_row_export() -> None:
    shots = import_trackman_csv(
        _fixture_path("trackman_session_export.csv").read_bytes(),
        source_name="trackman_session_export.csv",
    )

    assert len(shots) == 200
    assert isinstance(shots[0], ShotEvent)
    assert shots[0].source == "trackman"
    assert shots[0].club == "Driver"


def test_200_row_trackman_export_builds_profile_and_runs_pipeline() -> None:
    shots = import_trackman_csv(
        _fixture_path("trackman_session_export.csv").read_bytes(),
        source_name="trackman_session_export.csv",
    )
    profile = build_profile_from_shots(shots)

    assert isinstance(profile, PlayerProfile)
    assert len(profile.club_distances) >= 8
    assert profile.club_distances["Driver"] >= 260.0

    result = Pipeline(profile).run({"distance_to_target": 150, "strategy": "neutral"})
    assert result.decision is not None
    assert result.decision.primary_club in profile.club_distances


def test_trackman_imported_profile_changes_recommendation_vs_default(sample_profile) -> None:
    imported_profile = build_profile_from_shots(
        import_trackman_csv(
            _fixture_path("trackman_session_export.csv").read_bytes(),
            source_name="trackman_session_export.csv",
        )
    )

    raw_input = {"distance_to_target": 150, "strategy": "neutral"}
    default_result = Pipeline(sample_profile).run(raw_input)
    imported_result = Pipeline(imported_profile).run(raw_input)

    assert default_result.decision.primary_club != imported_result.decision.primary_club


def test_trackman_shots_can_be_saved_and_loaded(tmp_path) -> None:
    shots = import_trackman_csv(
        _fixture_path("trackman_session_export.csv").read_bytes(),
        source_name="trackman_session_export.csv",
    )

    saved_path = save_shots(shots, player_id=shots[0].player_id, base_dir=tmp_path)
    reloaded = load_shots(player_id=shots[0].player_id, base_dir=tmp_path)

    assert saved_path.exists()
    assert saved_path.suffix in {".parquet", ".jsonl"}
    assert len(reloaded) == len(shots)

