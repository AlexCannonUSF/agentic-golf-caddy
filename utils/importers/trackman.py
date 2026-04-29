# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""TrackMan CSV importer."""

from __future__ import annotations

from pathlib import Path

from models import ShotEvent
from utils.importers._helpers import (
    default_player_name,
    first_present,
    parse_optional_float,
    parse_optional_lie,
    parse_timestamp,
    read_csv_rows,
)


def import_trackman_csv(data: bytes | str, *, source_name: str | Path = "trackman.csv") -> list[ShotEvent]:
    """Parse a TrackMan session export into normalized shot events."""

    rows, _ = read_csv_rows(data)
    shots: list[ShotEvent] = []

    for row in rows:
        player_id = first_present(row, "player", "player_name") or default_player_name(source_name)
        carry = parse_optional_float(first_present(row, "carry", "carry_yds", "carry_yards"))
        total = parse_optional_float(first_present(row, "total", "total_yds", "total_yards")) or carry
        if carry is None or total is None:
            continue

        shots.append(
            ShotEvent(
                player_id=player_id,
                club=first_present(row, "club") or "Unknown Club",
                carry_yds=carry,
                total_yds=total,
                launch_speed_mph=parse_optional_float(first_present(row, "ball_speed", "ball_speed_mph")),
                spin_rpm=parse_optional_float(first_present(row, "spin_rate", "spin_rpm", "spin")),
                offline_ft=parse_optional_float(first_present(row, "offline", "offline_ft")),
                lie=parse_optional_lie(first_present(row, "lie")),
                source="trackman",
                captured_at=parse_timestamp(first_present(row, "captured_at", "timestamp", "date_time", "date")),
            )
        )

    return shots

