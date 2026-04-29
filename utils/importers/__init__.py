# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Shot-history import helpers."""

from __future__ import annotations

from pathlib import Path

from models import PlayerProfile, ShotEvent
from utils.importers._helpers import normalize_header, read_csv_rows, slugify_player_id
from utils.importers.foresight import import_foresight_csv
from utils.importers.golfpad import import_golfpad_csv
from utils.importers.normalizer import build_profile_from_shots, build_tendencies, load_shots, save_shots
from utils.importers.trackman import import_trackman_csv


def detect_import_format(headers: list[str]) -> str:
    """Detect which importer should be used from a CSV header row."""

    # Each supported source has a different set of column names. Normalizing the
    # headers lets the app tolerate capitalization and spacing differences.
    normalized = {normalize_header(header) for header in headers}
    if {"club", "carry", "spin_rate"} <= normalized or {"club", "carry_yds", "spin_rate"} <= normalized:
        return "trackman"
    if {"club", "carry_yards", "backspin_rpm"} <= normalized:
        return "foresight"
    if {"club", "shot_distance_yards", "fairway_offset_ft"} <= normalized:
        return "golfpad"
    raise ValueError("Could not detect import format from CSV headers.")


def import_shot_file(data: bytes | str, *, source_name: str) -> tuple[str, list[ShotEvent]]:
    """Detect and import a shot file from raw CSV bytes/text."""

    _, headers = read_csv_rows(data)
    format_name = detect_import_format(headers)
    # After detection, delegate to the source-specific parser so each importer
    # only needs to understand one vendor format.
    if format_name == "trackman":
        return format_name, import_trackman_csv(data, source_name=source_name)
    if format_name == "foresight":
        return format_name, import_foresight_csv(data, source_name=source_name)
    return format_name, import_golfpad_csv(data, source_name=source_name)


def save_imported_profile(
    shots: list[ShotEvent],
    *,
    profile_name: str | None = None,
    base_dir: str | Path | None = None,
) -> tuple[PlayerProfile, Path]:
    """Persist shot history and rebuild the corresponding profile."""

    if not shots:
        raise ValueError("No shots were parsed from the uploaded file.")
    player_id = shots[0].player_id
    # Save the raw normalized shots and rebuild the profile from the same list
    # so future recommendations use the imported distances immediately.
    storage_path = save_shots(shots, player_id=player_id, base_dir=base_dir)
    profile = build_profile_from_shots(shots, profile_name=profile_name)
    return profile, storage_path


__all__ = [
    "build_profile_from_shots",
    "build_tendencies",
    "detect_import_format",
    "import_foresight_csv",
    "import_golfpad_csv",
    "import_shot_file",
    "import_trackman_csv",
    "load_shots",
    "save_imported_profile",
    "save_shots",
    "slugify_player_id",
]
