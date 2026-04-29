# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Elevation lookups backed by the USGS EPQS service."""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

from models import LatLon
from utils.config import http_timeout_seconds
from utils.data_sources.cache import DiskCache

logger = logging.getLogger(__name__)

_CACHE = DiskCache()
_EPQS_URL = "https://epqs.nationalmap.gov/v1/json"


def _fetch_elevation_payload(lat: float, lon: float) -> dict[str, object]:
    params = urllib.parse.urlencode(
        {
            "x": lon,
            "y": lat,
            "units": "Feet",
            "wkid": 4326,
            "includeDate": "false",
        }
    )
    request = urllib.request.Request(_EPQS_URL + "?" + params)
    with urllib.request.urlopen(request, timeout=http_timeout_seconds()) as response:
        return json.loads(response.read().decode("utf-8"))


def get_elevation(lat: float, lon: float, *, cache: DiskCache | None = None) -> float:
    """Fetch ground elevation in feet for a single coordinate."""

    location = LatLon(lat=lat, lon=lon)
    active_cache = cache or _CACHE
    key = {"lat": location.lat, "lon": location.lon, "units": "feet"}
    cached_payload = active_cache.get("usgs_epqs", key)
    if cached_payload is not None:
        logger.info("USGS elevation cache hit for %.6f, %.6f", location.lat, location.lon)
        return round(float(cached_payload["value"]), 1)

    # USGS returns elevation for one coordinate. The context agent catches
    # failures and falls back to manually entered elevation/altitude fields.
    logger.info("USGS elevation request for %.6f, %.6f", location.lat, location.lon)
    payload = _fetch_elevation_payload(location.lat, location.lon)
    if "value" not in payload:
        raise ValueError("USGS EPQS payload did not include an elevation value.")

    active_cache.set("usgs_epqs", key, {"value": payload["value"]})
    return round(float(payload["value"]), 1)


def get_elevation_delta(
    start: LatLon | tuple[float, float],
    end: LatLon | tuple[float, float],
    *,
    cache: DiskCache | None = None,
) -> float:
    """Return end elevation minus start elevation in feet."""

    start_location = start if isinstance(start, LatLon) else LatLon(lat=start[0], lon=start[1])
    end_location = end if isinstance(end, LatLon) else LatLon(lat=end[0], lon=end[1])

    # Delta is end minus start. Positive means the target is uphill from the
    # player, negative means downhill.
    start_elevation = get_elevation(start_location.lat, start_location.lon, cache=cache)
    end_elevation = get_elevation(end_location.lat, end_location.lon, cache=cache)
    return round(end_elevation - start_elevation, 1)
