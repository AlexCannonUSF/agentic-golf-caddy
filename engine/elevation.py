"""Elevation adjustment calculator."""

from models import Elevation

_ELEVATION_ADJUSTMENTS = {
    Elevation.FLAT: 0.0,
    Elevation.UPHILL: 5.0,
    Elevation.STEEP_UPHILL: 10.0,
    Elevation.DOWNHILL: -5.0,
    Elevation.STEEP_DOWNHILL: -10.0,
}


def calculate_elevation_adjustment(elevation: Elevation | str) -> float:
    """Return distance adjustment in yards from elevation change."""

    normalized = Elevation(elevation)
    return _ELEVATION_ADJUSTMENTS[normalized]
