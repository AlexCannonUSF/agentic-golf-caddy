# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Golf Pad CSV importer."""

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


def import_golfpad_csv(data: bytes | str, *, source_name: str | Path = "golfpad.csv") -> list[ShotEvent]:
    """Parse a Golf Pad export into normalized shot events."""

    rows, _ = read_csv_rows(data)
    shots: list[ShotEvent] = []

    for row in rows:
        player_id = first_present(row, "player", "player_name") or default_player_name(source_name)
        carry = parse_optional_float(
            first_present(
                row,
                "shot_distance_yards",
                "shot_distance",
                "carry_yards",
                "carry",
            )
        )
        total = parse_optional_float(first_present(row, "total_yards", "total")) or carry
        if carry is None or total is None:
            continue

        shots.append(
            ShotEvent(
                player_id=player_id,
                club=first_present(row, "club") or "Unknown Club",
                carry_yds=carry,
                total_yds=total,
                launch_speed_mph=parse_optional_float(first_present(row, "ball_speed_mph", "ball_speed")),
                spin_rpm=parse_optional_float(first_present(row, "spin_rpm", "spin")),
                offline_ft=parse_optional_float(
                    first_present(row, "fairway_offset_ft", "offline_ft", "offline", "target_offset_ft")
                ),
                lie=parse_optional_lie(first_present(row, "lie")),
                source="golfpad",
                captured_at=parse_timestamp(first_present(row, "played_at", "captured_at", "date")),
            )
        )

    return shots

