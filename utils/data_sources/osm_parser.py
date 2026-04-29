"""Convert Overpass golf-course payloads into normalized course models."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from models import Course, Green, Hazard, Hole, LatLon, TeeBox
from utils.geometry import centroid, haversine_yards, nearest_point_distance_yards, point_in_polygon


def _slugify_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_")
    if not slug:
        raise ValueError("Course name must include at least one alphanumeric character.")
    return slug


def _extract_geometry(element: dict[str, Any]) -> list[LatLon]:
    # Overpass geometry is a list of raw lat/lon dictionaries. Convert it to the
    # same LatLon model the rest of the app uses.
    raw_points = element.get("geometry") or element.get("geom") or []
    geometry: list[LatLon] = []
    for point in raw_points:
        if not isinstance(point, dict):
            continue
        if "lat" not in point or "lon" not in point:
            continue
        geometry.append(LatLon(lat=point["lat"], lon=point["lon"]))
    return geometry


def _ensure_polygon(points: list[LatLon]) -> list[LatLon]:
    if len(points) >= 3:
        return points
    if len(points) == 2:
        return [points[0], points[1], points[0]]
    if len(points) == 1:
        return [points[0], points[0], points[0]]
    return points


def _parse_hole_number(tags: dict[str, Any]) -> int | None:
    for key in ("ref", "hole"):
        raw_value = tags.get(key)
        if raw_value is None:
            continue
        match = re.search(r"\d+", str(raw_value))
        if match:
            number = int(match.group(0))
            if 1 <= number <= 36:
                return number

    name = str(tags.get("name", "")).strip()
    match = re.search(r"(?<!\d)([1-9]|[12]\d|3[0-6])(?!\d)", name)
    if match:
        return int(match.group(1))
    return None


def _parse_par(tags: dict[str, Any]) -> int:
    raw_par = tags.get("par")
    if raw_par is None:
        return 4
    try:
        parsed = int(str(raw_par).strip())
    except ValueError:
        return 4
    return parsed if 3 <= parsed <= 6 else 4


def _hazard_kind(tags: dict[str, Any]) -> str | None:
    golf_tag = str(tags.get("golf", "")).strip().lower()
    natural = str(tags.get("natural", "")).strip().lower()
    landuse = str(tags.get("landuse", "")).strip().lower()

    if golf_tag == "bunker":
        return "bunker"
    if golf_tag in {"water_hazard", "lateral_water_hazard"} or natural == "water":
        return "water"
    if landuse == "forest" or natural in {"wood", "tree_row", "tree"}:
        return "trees"
    if golf_tag == "out_of_bounds":
        return "ob"
    return None


def _choose_hole_number(
    center: LatLon,
    explicit_number: int | None,
    hole_anchors: dict[int, dict[str, Any]],
) -> int | None:
    # OSM features are not always tagged with a hole number. If a feature does
    # not say which hole it belongs to, assign it by containment or nearest hole.
    if explicit_number is not None and explicit_number in hole_anchors:
        return explicit_number

    containing_holes = [
        number
        for number, anchor in hole_anchors.items()
        if point_in_polygon(center, anchor["polygon"])
    ]
    if containing_holes:
        return min(
            containing_holes,
            key=lambda number: haversine_yards(center, anchor_center(hole_anchors[number])),
        )

    if not hole_anchors:
        return explicit_number

    return min(
        hole_anchors,
        key=lambda number: nearest_point_distance_yards(center, hole_anchors[number]["polygon"]),
    )


def anchor_center(anchor: dict[str, Any]) -> LatLon:
    """Return the center point used when assigning OSM elements to holes."""

    return anchor["center"]


def _tee_label(tags: dict[str, Any], fallback_index: int, green_center: LatLon, tee_center: LatLon) -> str:
    raw_label = (
        str(tags.get("name", "")).strip()
        or str(tags.get("ref", "")).strip()
        or str(tags.get("colour", "")).strip()
        or str(tags.get("color", "")).strip()
    )
    if raw_label:
        return raw_label
    approx_yards = int(round(haversine_yards(tee_center, green_center)))
    return f"Tee {fallback_index} ({approx_yards}y)"


def parse_course_payload(
    payload: dict[str, Any],
    *,
    course_id: str | None = None,
    osm_ref: str | None = None,
) -> Course:
    """Parse an Overpass JSON payload into a normalized ``Course``."""

    elements = payload.get("elements")
    if not isinstance(elements, list) or not elements:
        raise ValueError("Overpass payload did not include any elements.")

    course_element: dict[str, Any] | None = None
    hole_anchors: dict[int, dict[str, Any]] = {}
    collected_tees: defaultdict[int, list[tuple[dict[str, Any], list[LatLon], LatLon]]] = defaultdict(list)
    collected_fairways: defaultdict[int, list[list[LatLon]]] = defaultdict(list)
    collected_greens: defaultdict[int, list[list[LatLon]]] = defaultdict(list)
    collected_hazards: defaultdict[int, list[tuple[str, list[LatLon], LatLon]]] = defaultdict(list)
    unassigned_hazards: list[tuple[str, list[LatLon], LatLon]] = []

    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags")
        if not isinstance(tags, dict):
            continue

        geometry = _extract_geometry(element)
        if not geometry:
            continue

        if tags.get("leisure") == "golf_course" or tags.get("golf") == "golf_course":
            if course_element is None or tags.get("name"):
                course_element = element

        golf_tag = str(tags.get("golf", "")).strip().lower()
        hole_number = _parse_hole_number(tags)
        center = centroid(geometry)

        if golf_tag == "hole" and hole_number is not None:
            # Hole objects act as anchors. Tees, greens, fairways, and hazards
            # are matched back to these anchors later.
            hole_anchors[hole_number] = {
                "polygon": geometry,
                "center": center,
                "par": _parse_par(tags),
            }

    if not hole_anchors:
        raise ValueError("Could not find any hole polygons in the Overpass payload.")

    for element in elements:
        if not isinstance(element, dict):
            continue
        tags = element.get("tags")
        if not isinstance(tags, dict):
            continue

        geometry = _extract_geometry(element)
        if not geometry:
            continue

        golf_tag = str(tags.get("golf", "")).strip().lower()
        if golf_tag not in {"tee", "fairway", "green", "bunker", "water_hazard", "lateral_water_hazard"}:
            hazard_kind = _hazard_kind(tags)
            if hazard_kind is None:
                continue
            golf_tag = hazard_kind

        if golf_tag == "hole":
            continue

        center = centroid(geometry)
        explicit_number = _parse_hole_number(tags)
        hole_number = _choose_hole_number(center, explicit_number, hole_anchors)
        if hole_number is None:
            continue

        if golf_tag == "tee":
            collected_tees[hole_number].append((tags, geometry, center))
        elif golf_tag == "fairway":
            collected_fairways[hole_number].append(geometry)
        elif golf_tag == "green":
            collected_greens[hole_number].append(geometry)
        else:
            hazard_kind = "water" if "water" in golf_tag else golf_tag
            # Explicitly numbered hazards go straight to that hole. Unnumbered
            # hazards are assigned by nearest/containing hole after this loop.
            target = collected_hazards if explicit_number is not None else None
            if target is not None:
                target[hole_number].append((hazard_kind, geometry, center))
            else:
                unassigned_hazards.append((hazard_kind, geometry, center))

    for hazard_kind, geometry, center in unassigned_hazards:
        hole_number = _choose_hole_number(center, None, hole_anchors)
        if hole_number is not None:
            collected_hazards[hole_number].append((hazard_kind, geometry, center))

    if course_element is not None:
        course_tags = course_element.get("tags", {})
        course_name = str(course_tags.get("name", "")).strip() or "Imported Course"
        course_geometry = _extract_geometry(course_element)
        course_location = centroid(course_geometry) if course_geometry else centroid(
            [anchor["center"] for anchor in hole_anchors.values()]
        )
    else:
        course_name = "Imported Course"
        course_location = centroid([anchor["center"] for anchor in hole_anchors.values()])

    holes: list[Hole] = []
    for number in sorted(hole_anchors):
        anchor = hole_anchors[number]
        # Pick the largest available fairway/green polygon for each hole. If OSM
        # is missing one, fall back to the broad hole polygon so the course still
        # loads and remains usable.
        fairway_polygon = max(
            collected_fairways.get(number, [anchor["polygon"]]),
            key=len,
        )
        if len(fairway_polygon) < 3:
            fairway_polygon = anchor["polygon"]
        fairway_polygon = _ensure_polygon(fairway_polygon)

        green_polygon = max(
            collected_greens.get(number, [anchor["polygon"]]),
            key=len,
        )
        if len(green_polygon) < 3:
            green_polygon = anchor["polygon"]
        green_polygon = _ensure_polygon(green_polygon)
        green_center = centroid(green_polygon)

        tees: list[TeeBox] = []
        tee_candidates = sorted(
            collected_tees.get(number, []),
            key=lambda item: haversine_yards(item[2], green_center),
            reverse=True,
        )
        for index, (tags, geometry, tee_center) in enumerate(tee_candidates, start=1):
            label = _tee_label(tags, index, green_center, tee_center)
            tees.append(
                TeeBox(
                    label=label,
                    color=str(tags.get("colour", "")).strip() or str(tags.get("color", "")).strip() or None,
                    center=tee_center,
                    polygon=geometry,
                )
            )

        hazards: list[Hazard] = []
        reference_tee = tees[0].center if tees else anchor["center"]
        for hazard_kind, geometry, hazard_center in collected_hazards.get(number, []):
            hazards.append(
                Hazard(
                    kind=hazard_kind,
                    center=hazard_center,
                    polygon=_ensure_polygon(geometry),
                    carry_distance_yds=round(nearest_point_distance_yards(reference_tee, geometry), 1),
                )
            )

        holes.append(
            Hole(
                number=number,
                par=anchor["par"],
                tees=tees,
                fairway_polygon=fairway_polygon,
                green=Green(center=green_center, polygon=green_polygon),
                hazards=hazards,
            )
        )

    resolved_course_id = course_id or _slugify_name(course_name)
    return Course(
        id=resolved_course_id,
        name=course_name,
        location=course_location,
        holes=holes,
        osm_ref=osm_ref,
        source="osm_overpass",
    )
