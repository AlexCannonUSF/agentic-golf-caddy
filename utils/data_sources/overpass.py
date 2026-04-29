"""Overpass API connector for golf-course geometry."""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from typing import Any

from utils.config import http_timeout_seconds
from utils.data_sources.cache import DiskCache

logger = logging.getLogger(__name__)

_CACHE = DiskCache()
_DEFAULT_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def _normalize_osm_ref(osm_ref: int | str) -> str:
    raw = str(osm_ref).strip()
    if not raw:
        raise ValueError("osm_ref cannot be empty.")
    # Users can paste either "way/123", "relation/123", or just "123".
    # A plain number is treated as a way because that is common for course data.
    if "/" in raw:
        osm_type, osm_id = raw.split("/", 1)
        normalized_type = osm_type.strip().lower()
        if normalized_type not in {"way", "relation"}:
            raise ValueError("osm_ref must use way/<id> or relation/<id>.")
        if not osm_id.isdigit():
            raise ValueError("osm_ref id must be numeric.")
        return f"{normalized_type}/{osm_id}"

    if not raw.isdigit():
        raise ValueError("osm_ref must be numeric or use way/<id> or relation/<id>.")
    return f"way/{raw}"


def _build_query(normalized_ref: str) -> str:
    osm_type, osm_id = normalized_ref.split("/", 1)
    # The query starts from one course object, maps it to an area, then fetches
    # golf features and nearby hazards inside that area.
    return f"""[out:json][timeout:45];
{osm_type}({osm_id});
map_to_area->.searchArea;
(
  {osm_type}({osm_id});
  way(area.searchArea)[golf];
  relation(area.searchArea)[golf];
  way(area.searchArea)[natural=water];
  relation(area.searchArea)[natural=water];
  way(area.searchArea)[landuse=forest];
  relation(area.searchArea)[landuse=forest];
);
out tags geom;
"""


def _endpoint_candidates() -> list[str]:
    configured = os.getenv("OVERPASS_API_URL", "").strip()
    if configured:
        return [configured]
    return list(_DEFAULT_ENDPOINTS)


def _fetch_from_endpoint(endpoint: str, query: str) -> dict[str, Any]:
    request = urllib.request.Request(
        endpoint,
        data=query.encode("utf-8"),
        headers={"User-Agent": "AgenticGolfCaddy/1.0"},
    )
    with urllib.request.urlopen(request, timeout=http_timeout_seconds() * 6.0) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_course(
    osm_ref: int | str,
    *,
    cache: DiskCache | None = None,
) -> dict[str, Any]:
    """Fetch a golf-course payload from Overpass and cache it on disk."""

    normalized_ref = _normalize_osm_ref(osm_ref)
    active_cache = cache or _CACHE
    cache_key = {"osm_ref": normalized_ref}
    cached_payload = active_cache.get("overpass_course", cache_key)
    if cached_payload is not None:
        logger.info("Overpass course cache hit for %s", normalized_ref)
        return cached_payload

    query = _build_query(normalized_ref)
    last_error: Exception | None = None
    for endpoint in _endpoint_candidates():
        try:
            # Overpass mirrors can be unreliable, so try each configured endpoint
            # before giving up.
            logger.info("Overpass course request for %s via %s", normalized_ref, endpoint)
            payload = _fetch_from_endpoint(endpoint, query)
            active_cache.set("overpass_course", cache_key, payload)
            return payload
        except Exception as exc:  # pragma: no cover - exercised via retry behavior
            last_error = exc
            logger.warning("Overpass request failed for %s via %s: %s", normalized_ref, endpoint, exc)

    if last_error is not None:
        raise last_error
    raise RuntimeError(f"Failed to fetch course payload for {normalized_ref}.")
