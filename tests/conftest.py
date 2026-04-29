# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
import sys
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from models import Course, PlayerProfile, SkillLevel
from utils.data_sources.osm_parser import parse_course_payload
from utils.profile_manager import ProfileManager


@pytest.fixture
def sample_valid_shot_input() -> dict[str, object]:
    return {
        "distance_to_target": 150,
        "lie_type": "fairway",
        "wind_speed": 10,
        "wind_direction": "headwind",
        "elevation": "flat",
        "strategy": "neutral",
        "temperature": 72,
        "altitude_ft": 0,
    }


@pytest.fixture
def sample_club_distances() -> dict[str, float]:
    return {
        "Driver": 220,
        "3-wood": 200,
        "5-wood": 185,
        "4-hybrid": 175,
        "5-iron": 165,
        "6-iron": 155,
        "7-iron": 145,
        "8-iron": 135,
        "9-iron": 125,
        "PW": 115,
        "SW": 80,
        "LW": 60,
    }


@pytest.fixture
def sample_profile(sample_club_distances: dict[str, float]) -> PlayerProfile:
    return PlayerProfile(
        name="Alex Cannon",
        skill_level=SkillLevel.INTERMEDIATE,
        club_distances=sample_club_distances,
        preferred_shot="straight",
    )


@pytest.fixture
def temp_profile_dir(tmp_path: Path) -> Path:
    path = tmp_path / "profiles"
    path.mkdir(parents=True, exist_ok=True)
    return path


@pytest.fixture
def default_profiles_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "profiles"


@pytest.fixture
def profile_manager(temp_profile_dir: Path, default_profiles_dir: Path) -> ProfileManager:
    return ProfileManager(profile_dir=temp_profile_dir, default_profiles_dir=default_profiles_dir)


@pytest.fixture
def torrey_course_payload() -> dict[str, object]:
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "data_sources" / "overpass_torrey_south.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


@pytest.fixture
def torrey_course(torrey_course_payload: dict[str, object]) -> Course:
    return parse_course_payload(
        torrey_course_payload,
        course_id="torrey_pines_south",
        osm_ref="way/35679036",
    )
