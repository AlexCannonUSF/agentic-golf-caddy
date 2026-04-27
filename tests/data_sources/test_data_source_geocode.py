import json
from importlib import import_module
from pathlib import Path

from utils.data_sources.cache import DiskCache
from utils.data_sources.geocode import geocode


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


def test_geocode_parses_location_and_uses_cache(tmp_path, monkeypatch) -> None:
    payload = _fixture("nominatim_search.json")
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        return _DummyResponse(payload)

    geocode_module = import_module("utils.data_sources.geocode")

    monkeypatch.setattr(geocode_module.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(geocode_module, "_throttle_nominatim", lambda: None)

    cache = DiskCache(tmp_path / "cache")
    location = geocode("Bethpage Black Golf Course", cache=cache)
    assert location.lat == 40.748655
    assert location.lon == -73.445753

    cached_location = geocode("Bethpage Black Golf Course", cache=cache)
    assert cached_location == location
    assert calls["count"] == 1
