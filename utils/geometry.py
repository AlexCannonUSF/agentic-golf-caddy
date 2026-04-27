"""Lightweight geographic helpers for course and hazard reasoning."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

from models.environment import LatLon
from models.enums import PinPosition

_EARTH_RADIUS_M = 6_371_000.0
_YARDS_PER_METER = 1.0936133


def haversine_yards(start: LatLon, end: LatLon) -> float:
    """Return the great-circle distance between two coordinates in yards."""

    lat1 = math.radians(start.lat)
    lon1 = math.radians(start.lon)
    lat2 = math.radians(end.lat)
    lon2 = math.radians(end.lon)

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(_EARTH_RADIUS_M * c * _YARDS_PER_METER, 1)


def centroid(points: Sequence[LatLon]) -> LatLon:
    """Return the simple centroid of a polygon/polyline."""

    if not points:
        raise ValueError("At least one point is required to compute a centroid.")
    return LatLon(
        lat=sum(point.lat for point in points) / len(points),
        lon=sum(point.lon for point in points) / len(points),
    )


def bounding_box(points: Sequence[LatLon]) -> tuple[float, float, float, float]:
    """Return (min_lat, min_lon, max_lat, max_lon) for the input points."""

    if not points:
        raise ValueError("At least one point is required to compute a bounding box.")
    return (
        min(point.lat for point in points),
        min(point.lon for point in points),
        max(point.lat for point in points),
        max(point.lon for point in points),
    )


def point_in_polygon(point: LatLon, polygon: Sequence[LatLon]) -> bool:
    """Return True when *point* falls inside *polygon* using ray casting."""

    if len(polygon) < 3:
        return False

    x = point.lon
    y = point.lat
    inside = False
    j = len(polygon) - 1

    for i in range(len(polygon)):
        xi = polygon[i].lon
        yi = polygon[i].lat
        xj = polygon[j].lon
        yj = polygon[j].lat
        intersects = ((yi > y) != (yj > y)) and (
            x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi
        )
        if intersects:
            inside = not inside
        j = i

    return inside


def _project_to_local_yards(origin: LatLon, point: LatLon) -> tuple[float, float]:
    lat_scale = 69.0 * 1760.0
    lon_scale = math.cos(math.radians(origin.lat)) * lat_scale
    x = (point.lon - origin.lon) * lon_scale
    y = (point.lat - origin.lat) * lat_scale
    return x, y


def line_projection_metrics(
    start: LatLon,
    end: LatLon,
    point: LatLon,
) -> tuple[float, float, str]:
    """Return (along_ratio, lateral_yards, side) relative to the shot line."""

    sx, sy = 0.0, 0.0
    ex, ey = _project_to_local_yards(start, end)
    px, py = _project_to_local_yards(start, point)
    vx = ex - sx
    vy = ey - sy
    wx = px - sx
    wy = py - sy
    denom = (vx * vx) + (vy * vy)
    if denom <= 0.0:
        return 0.0, 0.0, "center"

    along_ratio = ((wx * vx) + (wy * vy)) / denom
    cross = (vx * wy) - (vy * wx)
    lateral_yards = abs(cross) / math.sqrt(denom)
    if abs(cross) < 1e-6:
        side = "center"
    else:
        side = "left" if cross > 0 else "right"
    return along_ratio, round(lateral_yards, 1), side


def nearest_point_distance_yards(point: LatLon, polygon: Iterable[LatLon]) -> float:
    """Return the nearest vertex distance from *point* to *polygon* in yards."""

    vertices = list(polygon)
    if not vertices:
        return float("inf")
    return min(haversine_yards(point, vertex) for vertex in vertices)


def green_reference_points(
    green_polygon: Sequence[LatLon],
    tee_location: LatLon,
) -> dict[PinPosition, LatLon]:
    """Return canonical front/middle/back pin coordinates for a green."""

    if len(green_polygon) < 3:
        raise ValueError("Green polygon must include at least 3 points.")

    green_center = centroid(green_polygon)
    along_points = [
        (line_projection_metrics(tee_location, green_center, point)[0], point)
        for point in green_polygon
    ]
    front_point = min(along_points, key=lambda item: item[0])[1]
    back_point = max(along_points, key=lambda item: item[0])[1]
    return {
        PinPosition.FRONT: front_point,
        PinPosition.MIDDLE: green_center,
        PinPosition.BACK: back_point,
    }


def derive_pin_position(
    pin_lat_lon: LatLon,
    green_polygon: Sequence[LatLon],
    tee_location: LatLon,
) -> PinPosition:
    """Infer front/middle/back from a pin coordinate and green shape."""

    if len(green_polygon) < 3:
        return PinPosition.MIDDLE

    green_center = centroid(green_polygon)
    along_values = [
        line_projection_metrics(tee_location, green_center, point)[0]
        for point in green_polygon
    ]
    front_value = min(along_values)
    back_value = max(along_values)
    pin_value = line_projection_metrics(tee_location, green_center, pin_lat_lon)[0]

    span = back_value - front_value
    if abs(span) < 1e-6:
        return PinPosition.MIDDLE

    normalized = (pin_value - front_value) / span
    if normalized <= 0.34:
        return PinPosition.FRONT
    if normalized >= 0.66:
        return PinPosition.BACK
    return PinPosition.MIDDLE
