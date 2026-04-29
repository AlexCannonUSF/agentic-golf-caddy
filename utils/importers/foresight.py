# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Foresight FSX CSV importer."""

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


def import_foresight_csv(data: bytes | str, *, source_name: str | Path = "foresight.csv") -> list[ShotEvent]:
    """Parse a Foresight FSX export into normalized shot events."""

    rows, _ = read_csv_rows(data)
    shots: list[ShotEvent] = []

    for row in rows:
        player_id = first_present(row, "player", "player_name") or default_player_name(source_name)
        carry = parse_optional_float(first_present(row, "carry_yards", "carry", "carry_yds"))
        total = parse_optional_float(first_present(row, "total_yards", "total", "total_yds")) or carry
        if carry is None or total is None:
            continue

        shots.append(
            ShotEvent(
                player_id=player_id,
                club=first_present(row, "club") or "Unknown Club",
                carry_yds=carry,
                total_yds=total,
                launch_speed_mph=parse_optional_float(first_present(row, "ball_speed_mph", "ball_speed")),
                spin_rpm=parse_optional_float(first_present(row, "backspin_rpm", "spin_rpm", "spin")),
                offline_ft=parse_optional_float(first_present(row, "offline_feet", "offline_ft", "offline")),
                lie=parse_optional_lie(first_present(row, "lie")),
                source="foresight",
                captured_at=parse_timestamp(first_present(row, "captured_at", "timestamp", "date")),
            )
        )

    return shots

