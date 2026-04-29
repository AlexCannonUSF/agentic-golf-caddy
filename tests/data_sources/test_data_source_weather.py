# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
import json
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path

from utils.data_sources.cache import DiskCache
from utils.data_sources.weather import get_weather


class _DummyResponse:
    def __init__(self, payload: object) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return self._body


def _fixture(name: str) -> object:
    path = Path(__file__).resolve().parents[1] / "fixtures" / "data_sources" / name
    return json.loads(path.read_text(encoding="utf-8"))


def test_get_weather_parses_current_and_uses_cache(tmp_path, monkeypatch) -> None:
    payload = _fixture("open_meteo_weather.json")
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        return _DummyResponse(payload)

    weather_module = import_module("utils.data_sources.weather")

    monkeypatch.setattr(weather_module.urllib.request, "urlopen", fake_urlopen)

    cache = DiskCache(tmp_path / "cache")
    observation = get_weather(40.7, -73.9, cache=cache)
    assert observation.wind_speed_mph == 7.7
    assert observation.wind_direction_deg == 173.0
    assert observation.temperature_f == 83.7
    assert observation.source == "open-meteo"

    cached_observation = get_weather(40.7, -73.9, cache=cache)
    assert cached_observation == observation
    assert calls["count"] == 1


def test_get_weather_uses_nearest_hourly_sample(tmp_path, monkeypatch) -> None:
    payload = _fixture("open_meteo_weather.json")

    def fake_urlopen(request, timeout):
        return _DummyResponse(payload)

    weather_module = import_module("utils.data_sources.weather")

    monkeypatch.setattr(weather_module.urllib.request, "urlopen", fake_urlopen)

    cache = DiskCache(tmp_path / "cache")
    observation = get_weather(
        40.7,
        -73.9,
        when=datetime(2026, 4, 15, 20, 10, tzinfo=timezone.utc),
        cache=cache,
    )

    assert observation.wind_speed_mph == 7.0
    assert observation.temperature_f == 80.2
    assert observation.observed_at.hour == 20
