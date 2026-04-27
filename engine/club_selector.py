"""Club matching algorithm with strategy-aware biasing and golf-specific guardrails."""

from __future__ import annotations

from dataclasses import dataclass

from models import (
    CandidateOption,
    LieType,
    PinPosition,
    PlayerProfile,
    STANDARD_BAG_ORDER,
    ShotContext,
    Strategy,
    TargetMode,
)


@dataclass(frozen=True)
class ClubSelection:
    """Primary and backup club selection output."""

    primary_club: str
    primary_distance: float
    backup_club: str
    backup_distance: float
    strategy_note: str


def _ordered_clubs(profile: PlayerProfile) -> list[tuple[str, float]]:
    clubs = profile.club_distances

    if all(club in clubs for club in STANDARD_BAG_ORDER):
        ordered = [(club, clubs[club]) for club in STANDARD_BAG_ORDER]
    else:
        ordered = sorted(clubs.items(), key=lambda item: item[1], reverse=True)

    return ordered


def _nearest_index(ordered_clubs: list[tuple[str, float]], target_distance: float) -> int:
    return min(
        range(len(ordered_clubs)),
        key=lambda idx: abs(ordered_clubs[idx][1] - target_distance),
    )


def _surrounding_indices(
    ordered_clubs: list[tuple[str, float]],
    target_distance: float,
) -> tuple[int | None, int | None]:
    """
    Return (longer_idx, shorter_idx) around the target.

    - longer_idx: nearest club that reaches/exceeds target
    - shorter_idx: nearest club that is below target
    """

    longer_candidates = [idx for idx, (_, dist) in enumerate(ordered_clubs) if dist >= target_distance]
    shorter_candidates = [idx for idx, (_, dist) in enumerate(ordered_clubs) if dist < target_distance]

    longer_idx = max(longer_candidates) if longer_candidates else None
    shorter_idx = min(shorter_candidates) if shorter_candidates else None
    return longer_idx, shorter_idx


def _select_primary_index(
    ordered_clubs: list[tuple[str, float]],
    target_distance: float,
    strategy: Strategy,
) -> int:
    nearest_idx = _nearest_index(ordered_clubs, target_distance)
    longer_idx, shorter_idx = _surrounding_indices(ordered_clubs, target_distance)

    # Strategy bias applies only when target falls between two clubs.
    between_two_clubs = longer_idx is not None and shorter_idx is not None
    if not between_two_clubs:
        return nearest_idx

    if strategy == Strategy.SAFE:
        return shorter_idx
    if strategy == Strategy.AGGRESSIVE:
        return longer_idx
    return nearest_idx


def _club_family(club_name: str) -> str:
    normalized = club_name.strip().lower()
    if normalized == "driver":
        return "driver"
    if "wood" in normalized:
        return "wood"
    if "hybrid" in normalized:
        return "hybrid"
    if normalized.endswith("iron"):
        prefix = normalized.split("-", 1)[0]
        try:
            iron_number = int(prefix)
        except ValueError:
            return "iron"
        if iron_number <= 5:
            return "long_iron"
        if iron_number <= 7:
            return "mid_iron"
        return "short_iron"
    if normalized in {"pw", "gw", "aw", "sw", "lw"}:
        return "wedge"
    return "other"


def _strategy_side_penalty(club_distance: float, target_distance: float, strategy: Strategy) -> float:
    distance_gap = club_distance - target_distance
    if strategy == Strategy.SAFE and distance_gap > 0:
        return round(8.0 + min(8.0, distance_gap * 0.8), 2)
    if strategy == Strategy.AGGRESSIVE and distance_gap < 0:
        return round(8.0 + min(8.0, abs(distance_gap) * 0.8), 2)
    return 0.0


def _lie_penalty(club_name: str, target_distance: float, shot_context: ShotContext | None) -> float:
    if shot_context is None:
        return 0.0

    family = _club_family(club_name)
    lie_type = shot_context.lie_type
    penalty = 0.0

    if family == "driver" and lie_type != LieType.TEE:
        penalty += 18.0 if target_distance <= 240.0 else 10.0

    if lie_type == LieType.BUNKER:
        if family == "driver":
            penalty += 110.0
        elif family == "wood":
            penalty += 40.0
        elif family == "hybrid":
            penalty += 24.0
        elif family == "long_iron":
            penalty += 16.0
        elif family == "mid_iron":
            penalty += 6.0

        if target_distance <= 190.0 and family in {"wood", "hybrid", "long_iron"}:
            penalty += 12.0

    elif lie_type == LieType.DEEP_ROUGH:
        if family == "driver":
            penalty += 50.0
        elif family == "wood":
            penalty += 14.0
        elif family == "hybrid":
            penalty += 6.0
        elif family == "long_iron":
            penalty += 7.0

    elif lie_type == LieType.ROUGH:
        if family == "driver":
            penalty += 20.0
        elif family == "wood":
            penalty += 4.0
        elif family == "hybrid":
            penalty += 1.5
        elif family == "long_iron":
            penalty += 2.0

    return round(penalty, 2)


def _tendency_penalty(club_name: str, player_profile: PlayerProfile) -> float:
    tendencies = player_profile.tendencies
    penalty = 0.0

    confidence = tendencies.confidence_by_club.get(club_name)
    if confidence is not None:
        penalty += (0.78 - confidence) * 6.0

    dispersion = tendencies.dispersion_by_club.get(club_name)
    if dispersion is not None and dispersion > 14.0:
        penalty += (dispersion - 14.0) * 0.18

    return round(penalty, 2)


def _context_penalty(club_distance: float, target_distance: float, shot_context: ShotContext | None) -> float:
    if shot_context is None:
        return 0.0

    penalty = 0.0
    hazard_note = (shot_context.hazard_note or "").lower()

    if any(token in hazard_note for token in ("water_short", "bunker_short", "must_carry")) and club_distance < target_distance:
        penalty += 4.0
    if any(token in hazard_note for token in ("water_long", "bunker_long", "trouble_long")) and club_distance > target_distance:
        penalty += 4.0

    if shot_context.target_mode == TargetMode.CENTER_GREEN and club_distance > target_distance + 12.0:
        penalty += 2.0
    if shot_context.target_mode == TargetMode.LAYUP and club_distance > target_distance:
        penalty += 6.0

    if shot_context.pin_position == PinPosition.BACK and club_distance < target_distance - 3.0:
        penalty += 1.5
    if shot_context.pin_position == PinPosition.FRONT and club_distance > target_distance + 3.0:
        penalty += 1.5

    if shot_context.player_confidence is not None and shot_context.player_confidence <= 2:
        if club_distance < target_distance - 8.0:
            penalty += 2.0
        elif club_distance > target_distance + 12.0:
            penalty += 1.0

    return round(penalty, 2)


def _club_score(
    club_name: str,
    club_distance: float,
    target_distance: float,
    player_profile: PlayerProfile,
    strategy: Strategy,
    shot_context: ShotContext | None,
) -> float:
    return round(
        abs(club_distance - target_distance)
        + _strategy_side_penalty(club_distance, target_distance, strategy)
        + _lie_penalty(club_name, target_distance, shot_context)
        + _tendency_penalty(club_name, player_profile)
        + _context_penalty(club_distance, target_distance, shot_context),
        2,
    )


def _rank_indices(
    ordered_clubs: list[tuple[str, float]],
    target_distance: float,
    player_profile: PlayerProfile,
    strategy: Strategy,
    shot_context: ShotContext | None,
) -> list[int]:
    ranked = sorted(
        range(len(ordered_clubs)),
        key=lambda idx: (
            _club_score(
                ordered_clubs[idx][0],
                ordered_clubs[idx][1],
                target_distance,
                player_profile,
                strategy,
                shot_context,
            ),
            abs(ordered_clubs[idx][1] - target_distance),
            -ordered_clubs[idx][1],
        ),
    )
    return ranked


def _select_backup_index(
    ordered_clubs: list[tuple[str, float]],
    primary_index: int,
    target_distance: float,
    ranked_indices: list[int],
) -> int:
    primary_distance = ordered_clubs[primary_index][1]
    if primary_distance < target_distance:
        opposite_side = [
            idx
            for idx, (_, distance) in enumerate(ordered_clubs)
            if distance >= target_distance and idx != primary_index
        ]
    else:
        opposite_side = [
            idx
            for idx, (_, distance) in enumerate(ordered_clubs)
            if distance < target_distance and idx != primary_index
        ]

    if opposite_side:
        return min(
            opposite_side,
            key=lambda idx: (abs(ordered_clubs[idx][1] - target_distance), -ordered_clubs[idx][1]),
        )

    for idx in ranked_indices:
        if idx != primary_index:
            return idx

    return primary_index


def _strategy_note(strategy: Strategy, primary_club: str, primary_distance: float, target_distance: float) -> str:
    diff = round(primary_distance - target_distance, 1)
    if strategy == Strategy.SAFE:
        return (
            f"Safe bias: selected {primary_club} ({primary_distance:.0f} avg) "
            f"to reduce overshoot risk ({diff:+.1f} yds vs plays-like)."
        )
    if strategy == Strategy.AGGRESSIVE:
        return (
            f"Aggressive bias: selected {primary_club} ({primary_distance:.0f} avg) "
            f"to ensure carry ({diff:+.1f} yds vs plays-like)."
        )
    return (
        f"Neutral pick: {primary_club} ({primary_distance:.0f} avg) "
        f"is the closest match ({diff:+.1f} yds vs plays-like)."
    )


def select_clubs(
    plays_like_distance: float,
    player_profile: PlayerProfile,
    strategy: Strategy | str,
    shot_context: ShotContext | None = None,
) -> ClubSelection:
    """Select primary and backup clubs for the given plays-like distance."""

    ordered = _ordered_clubs(player_profile)
    if not ordered:
        raise ValueError("Player profile has no clubs configured.")

    normalized_strategy = Strategy(strategy)
    ranked_indices = _rank_indices(
        ordered,
        plays_like_distance,
        player_profile,
        normalized_strategy,
        shot_context,
    )

    primary_idx = ranked_indices[0]
    backup_idx = _select_backup_index(ordered, primary_idx, plays_like_distance, ranked_indices)

    primary_club, primary_distance = ordered[primary_idx]
    backup_club, backup_distance = ordered[backup_idx]

    if primary_club == backup_club and len(ordered) > 1:
        backup_idx = ranked_indices[1] if len(ranked_indices) > 1 else (primary_idx + 1 if primary_idx + 1 < len(ordered) else primary_idx - 1)
        backup_club, backup_distance = ordered[backup_idx]

    return ClubSelection(
        primary_club=primary_club,
        primary_distance=primary_distance,
        backup_club=backup_club,
        backup_distance=backup_distance,
        strategy_note=_strategy_note(
            normalized_strategy,
            primary_club=primary_club,
            primary_distance=primary_distance,
            target_distance=plays_like_distance,
        ),
    )


def rank_candidate_options(
    plays_like_distance: float,
    player_profile: PlayerProfile,
    *,
    limit: int = 3,
    shot_context: ShotContext | None = None,
) -> list[CandidateOption]:
    """Return the closest deterministic candidate clubs for bounded AI selection."""

    ordered = _ordered_clubs(player_profile)
    ranked_indices = _rank_indices(
        ordered,
        plays_like_distance,
        player_profile,
        Strategy.NEUTRAL,
        shot_context,
    )
    top_candidates = [ordered[idx] for idx in ranked_indices[: max(1, limit)]]
    return [
        CandidateOption(
            club_name=club_name,
            club_distance=club_distance,
            distance_gap=round(abs(club_distance - plays_like_distance), 1),
        )
        for club_name, club_distance in top_candidates
    ]
