# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
import json
from importlib import import_module
from pathlib import Path

from utils.data_sources.cache import DiskCache
from utils.data_sources.elevation import get_elevation, get_elevation_delta


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


def test_get_elevation_parses_payload_and_uses_cache(tmp_path, monkeypatch) -> None:
    payload = _fixture("usgs_elevation.json")
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        return _DummyResponse(payload)

    elevation_module = import_module("utils.data_sources.elevation")

    monkeypatch.setattr(elevation_module.urllib.request, "urlopen", fake_urlopen)

    cache = DiskCache(tmp_path / "cache")
    elevation_ft = get_elevation(40.7, -73.9, cache=cache)
    assert elevation_ft == 78.5

    cached_elevation_ft = get_elevation(40.7, -73.9, cache=cache)
    assert cached_elevation_ft == elevation_ft
    assert calls["count"] == 1


def test_get_elevation_delta_uses_both_points(monkeypatch) -> None:
    elevation_module = import_module("utils.data_sources.elevation")

    def fake_get_elevation(lat, lon, *, cache=None):
        return 110.0 if round(lat, 1) == 40.8 else 90.0

    monkeypatch.setattr(elevation_module, "get_elevation", fake_get_elevation)

    delta_ft = get_elevation_delta((40.7, -73.9), (40.8, -73.9))
    assert delta_ft == 20.0
