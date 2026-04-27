"""Quick profile wizard utilities."""

from __future__ import annotations

from typing import Any

from models import PlayerProfile, PreferredShot, SkillLevel, STANDARD_BAG_ORDER

QUICK_WIZARD_ANCHOR_CLUBS: tuple[str, str, str] = ("Driver", "7-iron", "PW")


def _to_positive_distance(raw_value: Any, label: str) -> float:
    if isinstance(raw_value, bool):
        raise ValueError(f"{label} distance must be numeric.")
    try:
        value = float(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} distance must be numeric.") from exc
    if value <= 0:
        raise ValueError(f"{label} distance must be > 0.")
    return round(value, 1)


def _linear_interpolate(x0: int, y0: float, x1: int, y1: float, x: int) -> float:
    if x0 == x1:
        return y0
    ratio = (x - x0) / (x1 - x0)
    return y0 + (y1 - y0) * ratio


def interpolate_club_distances(
    driver_distance: Any,
    seven_iron_distance: Any,
    pitching_wedge_distance: Any,
) -> dict[str, float]:
    """
    Build a full bag from three anchor distances:
    Driver, 7-iron, and PW.
    """

    driver = _to_positive_distance(driver_distance, "Driver")
    seven_iron = _to_positive_distance(seven_iron_distance, "7-iron")
    pitching_wedge = _to_positive_distance(pitching_wedge_distance, "PW")

    if not driver > seven_iron > pitching_wedge:
        raise ValueError("Anchor distances must satisfy Driver > 7-iron > PW.")

    idx_driver = STANDARD_BAG_ORDER.index("Driver")
    idx_seven_iron = STANDARD_BAG_ORDER.index("7-iron")
    idx_pw = STANDARD_BAG_ORDER.index("PW")

    distances: dict[str, float] = {}
    for idx, club in enumerate(STANDARD_BAG_ORDER):
        if idx <= idx_seven_iron:
            value = _linear_interpolate(idx_driver, driver, idx_seven_iron, seven_iron, idx)
        elif idx <= idx_pw:
            value = _linear_interpolate(idx_seven_iron, seven_iron, idx_pw, pitching_wedge, idx)
        else:
            # Wedges typically have larger gaps than short irons.
            sw_gap = max(25.0, min(35.0, round((seven_iron - pitching_wedge) * 0.9, 1)))
            lw_gap = 20.0
            if club == "SW":
                value = pitching_wedge - sw_gap
            else:
                value = (pitching_wedge - sw_gap) - lw_gap
        distances[club] = round(value, 1)

    # Ensure strictly descending distances even for extreme/edge anchor values.
    previous = float("inf")
    for club in STANDARD_BAG_ORDER:
        current = distances[club]
        if current >= previous:
            current = round(previous - 5.0, 1)
            distances[club] = current
        previous = current

    return distances


def build_profile_from_quick_calibration(
    name: str,
    skill_level: SkillLevel | str,
    *,
    driver_distance: Any,
    seven_iron_distance: Any,
    pitching_wedge_distance: Any,
    preferred_shot: PreferredShot | str = PreferredShot.STRAIGHT,
) -> PlayerProfile:
    """Create a full PlayerProfile from quick 3-club calibration inputs."""

    club_distances = interpolate_club_distances(
        driver_distance=driver_distance,
        seven_iron_distance=seven_iron_distance,
        pitching_wedge_distance=pitching_wedge_distance,
    )
    return PlayerProfile(
        name=name,
        skill_level=skill_level,
        club_distances=club_distances,
        preferred_shot=preferred_shot,
    )
