"""Shot-history normalization, storage, and profile rebuilding helpers."""

from __future__ import annotations

import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable, Sequence

from models import PlayerProfile, PlayerTendencies, PreferredShot, ShotEvent, SkillLevel
from utils.config import data_dir
from utils.importers._helpers import slugify_player_id


def _trimmed(values: Sequence[float], trim_ratio: float = 0.1) -> list[float]:
    ordered = sorted(values)
    if len(ordered) < 5:
        return list(ordered)
    trim_count = max(0, int(len(ordered) * trim_ratio))
    if trim_count * 2 >= len(ordered):
        return list(ordered)
    return ordered[trim_count : len(ordered) - trim_count]


def _skill_level_from_driver(driver_distance: float | None) -> SkillLevel:
    if driver_distance is None:
        return SkillLevel.INTERMEDIATE
    if driver_distance >= 260.0:
        return SkillLevel.SCRATCH
    if driver_distance >= 235.0:
        return SkillLevel.ADVANCED
    if driver_distance >= 205.0:
        return SkillLevel.INTERMEDIATE
    return SkillLevel.BEGINNER


def _profile_name_from_player_id(player_id: str) -> str:
    parts = [part for part in slugify_player_id(player_id).split("_") if part]
    return " ".join(part.capitalize() for part in parts) or "Imported Player"


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def build_tendencies(shots: Iterable[ShotEvent]) -> PlayerTendencies:
    """Build player tendencies from normalized shot history."""

    shot_list = list(shots)
    if not shot_list:
        return PlayerTendencies()

    miss_counter: Counter[str] = Counter()
    club_carry_values: defaultdict[str, list[float]] = defaultdict(list)
    club_offline_values: defaultdict[str, list[float]] = defaultdict(list)
    all_offline_values: list[float] = []

    for shot in shot_list:
        club_carry_values[shot.club].append(shot.carry_yds)
        if shot.offline_ft is not None:
            club_offline_values[shot.club].append(shot.offline_ft)
            all_offline_values.append(shot.offline_ft)
            if shot.offline_ft <= -15.0:
                miss_counter["left"] += 1
            elif shot.offline_ft >= 15.0:
                miss_counter["right"] += 1

    common_miss = miss_counter.most_common(1)[0][0] if miss_counter else None

    shot_shape = PreferredShot.STRAIGHT
    if all_offline_values:
        average_offline = _mean(all_offline_values)
        if average_offline <= -8.0:
            shot_shape = PreferredShot.DRAW
        elif average_offline >= 8.0:
            shot_shape = PreferredShot.FADE

    confidence_by_club: dict[str, float] = {}
    dispersion_by_club: dict[str, float] = {}
    for club, carry_values in club_carry_values.items():
        # More consistent carry numbers produce higher confidence. Offline miss
        # distance is folded into dispersion so strategy can avoid risky clubs.
        carry_mean = _mean(carry_values)
        carry_stddev = statistics.pstdev(carry_values) if len(carry_values) > 1 else 0.0
        raw_confidence = 1.0 - (carry_stddev / carry_mean) if carry_mean > 0 else 0.2
        confidence_by_club[club] = round(min(0.95, max(0.2, raw_confidence)), 2)

        offline_component = 0.0
        if club_offline_values[club]:
            offline_component = _mean([abs(value) for value in club_offline_values[club]]) / 3.0
        dispersion_by_club[club] = round(max(1.0, carry_stddev + offline_component), 1)

    return PlayerTendencies(
        common_miss=common_miss,
        shot_shape=shot_shape,
        confidence_by_club=confidence_by_club,
        dispersion_by_club=dispersion_by_club,
    )


def build_profile_from_shots(
    shots: Iterable[ShotEvent],
    *,
    profile_name: str | None = None,
) -> PlayerProfile:
    """Build a PlayerProfile from normalized shot history."""

    shot_list = list(shots)
    if not shot_list:
        raise ValueError("At least one shot is required to build a profile.")

    club_carry_values: defaultdict[str, list[float]] = defaultdict(list)
    for shot in shot_list:
        club_carry_values[shot.club].append(shot.carry_yds)

    club_distances: dict[str, float] = {}
    for club, values in club_carry_values.items():
        trimmed_values = _trimmed(values)
        club_distances[club] = round(statistics.median(trimmed_values), 1)

    player_id = shot_list[0].player_id
    tendencies = build_tendencies(shot_list)
    skill_level = _skill_level_from_driver(club_distances.get("Driver"))
    return PlayerProfile(
        name=profile_name or _profile_name_from_player_id(player_id),
        skill_level=skill_level,
        club_distances=club_distances,
        preferred_shot=tendencies.shot_shape or PreferredShot.STRAIGHT,
        tendencies=tendencies,
    )


def save_shots(
    shots: Iterable[ShotEvent],
    *,
    player_id: str,
    base_dir: str | Path | None = None,
) -> Path:
    """Persist normalized shot history as parquet when available, else JSONL."""

    shot_list = list(shots)
    root = Path(base_dir) if base_dir is not None else data_dir() / "players"
    player_dir = root / slugify_player_id(player_id)
    player_dir.mkdir(parents=True, exist_ok=True)

    records = [shot.model_dump(mode="json") for shot in shot_list]

    try:
        # Parquet is compact when pyarrow is installed; JSONL keeps the app
        # usable in a fresh student environment without optional dependencies.
        import pyarrow as pa
        import pyarrow.parquet as pq

        path = player_dir / "shots.parquet"
        table = pa.Table.from_pylist(records)
        pq.write_table(table, path)
        return path
    except Exception:
        path = player_dir / "shots.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        return path


def load_shots(
    *,
    player_id: str,
    base_dir: str | Path | None = None,
) -> list[ShotEvent]:
    """Load persisted shot history for a player."""

    root = Path(base_dir) if base_dir is not None else data_dir() / "players"
    player_dir = root / slugify_player_id(player_id)
    parquet_path = player_dir / "shots.parquet"
    jsonl_path = player_dir / "shots.jsonl"

    if parquet_path.exists():
        import pyarrow.parquet as pq

        table = pq.read_table(parquet_path)
        return [ShotEvent.model_validate(row) for row in table.to_pylist()]

    if jsonl_path.exists():
        return [
            ShotEvent.model_validate(json.loads(line))
            for line in jsonl_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    return []
