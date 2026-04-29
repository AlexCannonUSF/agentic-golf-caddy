# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
import json
from importlib import import_module
from pathlib import Path

from utils.data_sources.cache import DiskCache
from utils.data_sources.overpass import fetch_course


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


def test_fetch_course_parses_response_and_uses_cache(tmp_path, monkeypatch) -> None:
    payload = _fixture("overpass_torrey_south.json")
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        return _DummyResponse(payload)

    module = import_module("utils.data_sources.overpass")
    monkeypatch.setattr(module.urllib.request, "urlopen", fake_urlopen)

    cache = DiskCache(tmp_path / "cache")
    response = fetch_course("way/35679036", cache=cache)
    assert len(response["elements"]) == 252

    cached_response = fetch_course("35679036", cache=cache)
    assert cached_response == response
    assert calls["count"] == 1
