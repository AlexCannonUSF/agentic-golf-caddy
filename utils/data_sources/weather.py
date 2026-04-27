"""Weather lookups backed by the Open-Meteo API."""

from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from models import WeatherObservation
from utils.config import http_timeout_seconds
from utils.data_sources.cache import DiskCache

logger = logging.getLogger(__name__)

_CACHE = DiskCache()
_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def _bucket_for_time(when: datetime | None) -> str:
    reference = when.astimezone(timezone.utc) if when is not None else datetime.now(timezone.utc)
    minute_bucket = (reference.minute // 15) * 15
    bucketed = reference.replace(minute=minute_bucket, second=0, microsecond=0)
    return bucketed.isoformat()


def _fetch_weather_payload(lat: float, lon: float) -> dict[str, object]:
    params = urllib.parse.urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,wind_direction_10m",
            "hourly": "temperature_2m,relative_humidity_2m,pressure_msl,wind_speed_10m,wind_direction_10m",
            "wind_speed_unit": "mph",
            "temperature_unit": "fahrenheit",
            "timezone": "UTC",
        }
    )
    request = urllib.request.Request(_OPEN_METEO_URL + "?" + params)
    with urllib.request.urlopen(request, timeout=http_timeout_seconds()) as response:
        return json.loads(response.read().decode("utf-8"))


def _parse_current(payload: dict[str, object]) -> WeatherObservation:
    current = payload.get("current")
    if not isinstance(current, dict):
        raise ValueError("Open-Meteo payload did not include current weather data.")

    return WeatherObservation(
        wind_speed_mph=current["wind_speed_10m"],
        wind_direction_deg=current["wind_direction_10m"],
        temperature_f=current["temperature_2m"],
        humidity_pct=current.get("relative_humidity_2m"),
        pressure_mb=current.get("pressure_msl"),
        source="open-meteo",
        observed_at=current["time"] + ":00+00:00" if len(str(current["time"])) == 16 else current["time"],
    )


def _parse_hourly(payload: dict[str, object], when: datetime) -> WeatherObservation:
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise ValueError("Open-Meteo payload did not include hourly weather data.")

    times = list(hourly.get("time", []))
    if not times:
        raise ValueError("Open-Meteo hourly payload did not include timestamps.")

    target = when.astimezone(timezone.utc)
    normalized_times = [
        datetime.fromisoformat((timestamp + ":00+00:00") if len(timestamp) == 16 else timestamp.replace("Z", "+00:00"))
        for timestamp in times
    ]
    nearest_index = min(range(len(normalized_times)), key=lambda idx: abs(normalized_times[idx] - target))

    return WeatherObservation(
        wind_speed_mph=hourly["wind_speed_10m"][nearest_index],
        wind_direction_deg=hourly["wind_direction_10m"][nearest_index],
        temperature_f=hourly["temperature_2m"][nearest_index],
        humidity_pct=hourly.get("relative_humidity_2m", [None])[nearest_index],
        pressure_mb=hourly.get("pressure_msl", [None])[nearest_index],
        source="open-meteo",
        observed_at=normalized_times[nearest_index],
    )


def get_weather(
    lat: float,
    lon: float,
    when: datetime | None = None,
    *,
    cache: DiskCache | None = None,
) -> WeatherObservation:
    """Fetch weather for a location, using a 15-minute cache bucket."""

    active_cache = cache or _CACHE
    key = {
        "lat": round(float(lat), 4),
        "lon": round(float(lon), 4),
        "bucket": _bucket_for_time(when),
    }
    cached_payload = active_cache.get("open_meteo", key)
    if cached_payload is not None:
        logger.info("Open-Meteo weather cache hit for %.4f, %.4f", key["lat"], key["lon"])
        return WeatherObservation.model_validate(cached_payload)

    logger.info("Open-Meteo weather request for %.4f, %.4f", key["lat"], key["lon"])
    payload = _fetch_weather_payload(key["lat"], key["lon"])
    observation = _parse_current(payload) if when is None else _parse_hourly(payload, when)
    active_cache.set("open_meteo", key, observation.model_dump(mode="json"))
    return observation

