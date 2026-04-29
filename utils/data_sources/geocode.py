# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Geocoding helpers backed by Nominatim with local caching."""

from __future__ import annotations

import json
import logging
import time
import urllib.parse
import urllib.request
from threading import Lock

from models import LatLon
from utils.config import http_timeout_seconds, nominatim_user_agent
from utils.data_sources.cache import DiskCache

logger = logging.getLogger(__name__)

_CACHE = DiskCache()
_NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
_NOMINATIM_LOCK = Lock()
_LAST_NOMINATIM_REQUEST_AT = 0.0


def _throttle_nominatim() -> None:
    global _LAST_NOMINATIM_REQUEST_AT

    with _NOMINATIM_LOCK:
        # Nominatim asks clients to avoid rapid repeated requests. This simple
        # lock keeps even repeated button clicks at about one request per second.
        elapsed = time.monotonic() - _LAST_NOMINATIM_REQUEST_AT
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        _LAST_NOMINATIM_REQUEST_AT = time.monotonic()


def geocode(query: str, *, cache: DiskCache | None = None) -> LatLon:
    """Resolve a free-text course/location query into latitude/longitude."""

    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Geocode query cannot be blank.")

    active_cache = cache or _CACHE
    key = {"query": normalized_query.lower(), "format": "jsonv2", "limit": 1}
    cached_payload = active_cache.get("nominatim", key)
    if cached_payload is not None:
        logger.info("Nominatim geocode cache hit for %s", normalized_query)
        return LatLon.model_validate(cached_payload)

    params = urllib.parse.urlencode({"q": normalized_query, "format": "jsonv2", "limit": 1})
    request = urllib.request.Request(
        f"{_NOMINATIM_SEARCH_URL}?{params}",
        headers={"User-Agent": nominatim_user_agent()},
    )

    _throttle_nominatim()
    logger.info("Nominatim geocode request for %s", normalized_query)
    with urllib.request.urlopen(request, timeout=http_timeout_seconds()) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not payload:
        raise ValueError(f"No location found for query: {normalized_query}")

    location = LatLon(lat=payload[0]["lat"], lon=payload[0]["lon"])
    active_cache.set("nominatim", key, location.model_dump(mode="json"))
    return location
