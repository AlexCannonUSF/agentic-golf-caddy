# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Unit tests for Agent 1: ContextAgent."""

from datetime import datetime, timezone

import pytest

from agents.context_agent import ContextAgent
from models import ShotContext, WeatherObservation
from utils.course_manager import CourseManager
from utils.pin_manager import PinManager
from utils.validators import InputValidationError


@pytest.fixture
def agent() -> ContextAgent:
    return ContextAgent()


class TestContextAgentHappyPath:
    def test_valid_input_returns_shot_context(self, agent: ContextAgent, sample_valid_shot_input: dict) -> None:
        result = agent.run(sample_valid_shot_input)
        assert isinstance(result, ShotContext)
        assert result.distance_to_target == 150.0

    def test_defaults_applied_for_minimal_input(self, agent: ContextAgent) -> None:
        result = agent.run({"distance_to_target": 200})
        assert result.lie_type.value == "fairway"
        assert result.wind_speed == 0.0
        assert result.elevation.value == "flat"
        assert result.strategy.value == "neutral"
        assert result.temperature == 72.0
        assert result.altitude_ft == 0.0

    def test_aliases_normalized(self, agent: ContextAgent) -> None:
        result = agent.run({
            "distance_to_target": 150,
            "lie_type": "tee_box",
            "wind_direction": "into",
            "elevation": "steep_up",
            "strategy": "conservative",
        })
        assert result.lie_type.value == "tee"
        assert result.wind_direction.value == "headwind"
        assert result.elevation.value == "steep_uphill"
        assert result.strategy.value == "safe"

    def test_numeric_coercion(self, agent: ContextAgent) -> None:
        result = agent.run({"distance_to_target": "175.6", "wind_speed": "12"})
        assert result.distance_to_target == 175.6
        assert result.wind_speed == 12.0

    def test_wind_speed_clamped_to_max(self, agent: ContextAgent) -> None:
        result = agent.run({"distance_to_target": 150, "wind_speed": 45})
        assert result.wind_speed == 40.0

    def test_wind_speed_negative_clamped_to_zero(self, agent: ContextAgent) -> None:
        result = agent.run({"distance_to_target": 150, "wind_speed": -5})
        assert result.wind_speed == 0.0

    def test_live_weather_observation_overrides_manual_fields_when_requested(self, agent: ContextAgent) -> None:
        result = agent.run(
            {
                "distance_to_target": 150,
                "wind_speed": 2,
                "wind_direction": "tailwind",
                "temperature": 60,
                "altitude_ft": 0,
                "live_weather_requested": True,
                "weather_observation": WeatherObservation(
                    wind_speed_mph=12.4,
                    wind_direction_deg=90,
                    temperature_f=81.2,
                    pressure_mb=1011.4,
                    humidity_pct=40,
                    source="open-meteo",
                    observed_at=datetime(2026, 4, 15, 19, 30, tzinfo=timezone.utc),
                ),
                "shot_azimuth_deg": 90,
            }
        )
        assert result.wind_speed == 12.4
        assert result.temperature == 81.2
        assert result.wind_direction.value == "headwind"

    def test_live_elevation_delta_maps_to_enum(self, agent: ContextAgent, monkeypatch) -> None:
        monkeypatch.setattr("agents.context_agent.get_elevation", lambda lat, lon: 100.0)
        monkeypatch.setattr("agents.context_agent.get_elevation_delta", lambda start, end: -24.0)

        result = agent.run(
            {
                "distance_to_target": 150,
                "location": {"lat": 40.7, "lon": -73.9},
                "target_location": {"lat": 40.71, "lon": -73.89},
                "live_elevation_requested": True,
            }
        )
        assert result.altitude_ft == 100.0
        assert result.elevation.value == "steep_downhill"

    def test_live_data_failure_falls_back_to_manual_inputs(self, agent: ContextAgent, monkeypatch) -> None:
        monkeypatch.setattr("agents.context_agent.get_weather", lambda lat, lon: (_ for _ in ()).throw(RuntimeError("boom")))

        result = agent.run(
            {
                "distance_to_target": 150,
                "wind_speed": 9,
                "temperature": 68,
                "location": {"lat": 40.7, "lon": -73.9},
                "live_weather_requested": True,
            }
        )
        assert result.wind_speed == 9.0
        assert result.temperature == 68.0

    def test_saved_course_context_derives_layup_distance_for_long_hole(self, tmp_path, torrey_course) -> None:
        course_manager = CourseManager(tmp_path / "courses")
        course_manager.save_course(torrey_course)
        agent = ContextAgent(course_manager=course_manager)

        hole_1 = next(hole for hole in torrey_course.holes if hole.number == 1)
        tee = hole_1.tees[0]
        result = agent.run(
            {
                "course_id": "torrey_pines_south",
                "hole_number": 1,
                "tee_lat_lon": tee.center.model_dump(mode="json"),
            }
        )

        assert 30.0 <= result.distance_to_target <= 350.0
        assert result.target_mode.value == "layup"

    def test_saved_course_context_can_drive_live_elevation_lookup(self, tmp_path, torrey_course, monkeypatch) -> None:
        course_manager = CourseManager(tmp_path / "courses")
        course_manager.save_course(torrey_course)
        agent = ContextAgent(course_manager=course_manager)

        monkeypatch.setattr("agents.context_agent.get_elevation", lambda lat, lon: 315.0)
        monkeypatch.setattr("agents.context_agent.get_elevation_delta", lambda start, end: 18.0)

        result = agent.run(
            {
                "course_id": "torrey_pines_south",
                "hole_number": 3,
                "live_elevation_requested": True,
            }
        )

        assert result.altitude_ft == 315.0
        assert result.elevation.value == "uphill"

    def test_saved_pin_is_loaded_and_pin_position_is_derived(self, tmp_path, torrey_course) -> None:
        course_manager = CourseManager(tmp_path / "courses")
        course_manager.save_course(torrey_course)
        pin_manager = PinManager(tmp_path / "pins")
        hole_3 = next(hole for hole in torrey_course.holes if hole.number == 3)
        tee = hole_3.tees[0]
        back_pin = hole_3.green.polygon[-1]
        pin_manager.save_pin("torrey_pines_south", 3, back_pin, pin_date="2026-04-15")

        agent = ContextAgent(course_manager=course_manager, pin_manager=pin_manager)
        result = agent.run(
            {
                "course_id": "torrey_pines_south",
                "hole_number": 3,
                "tee_lat_lon": tee.center.model_dump(mode="json"),
                "pin_date": "2026-04-15",
                "pin_source": "saved",
            }
        )

        assert result.pin_lat_lon is not None
        assert result.origin_lat_lon is not None
        assert result.pin_position is not None

    def test_pin_position_preset_derives_pin_coordinates(self, tmp_path, torrey_course) -> None:
        course_manager = CourseManager(tmp_path / "courses")
        course_manager.save_course(torrey_course)
        agent = ContextAgent(course_manager=course_manager)

        result = agent.run(
            {
                "course_id": "torrey_pines_south",
                "hole_number": 3,
                "pin_source": "front",
            }
        )

        assert result.pin_lat_lon is not None
        assert result.pin_position.value == "front"

    def test_explicit_distance_is_not_overridden_by_selected_course_context(self, tmp_path, torrey_course) -> None:
        course_manager = CourseManager(tmp_path / "courses")
        course_manager.save_course(torrey_course)
        agent = ContextAgent(course_manager=course_manager)

        result = agent.run(
            {
                "distance_to_target": 130,
                "lie_type": "bunker",
                "course_id": "torrey_pines_south",
                "hole_number": 3,
                "pin_source": "front",
            }
        )

        assert result.distance_to_target == 130.0
        assert result.origin_lat_lon is None
        assert result.pin_position is not None
        assert result.elevation.value == "flat"


class TestContextAgentErrors:
    def test_missing_distance_raises(self, agent: ContextAgent) -> None:
        with pytest.raises(InputValidationError) as exc_info:
            agent.run({"lie_type": "fairway"})
        assert "distance_to_target" in str(exc_info.value)

    def test_distance_out_of_range_raises(self, agent: ContextAgent) -> None:
        with pytest.raises(InputValidationError):
            agent.run({"distance_to_target": 10})

    def test_invalid_lie_type_raises(self, agent: ContextAgent) -> None:
        with pytest.raises(InputValidationError) as exc_info:
            agent.run({"distance_to_target": 150, "lie_type": "zzz_invalid"})
        assert "lie_type" in str(exc_info.value)

    def test_non_numeric_distance_raises(self, agent: ContextAgent) -> None:
        with pytest.raises(InputValidationError):
            agent.run({"distance_to_target": "abc"})

    def test_multiple_errors_collected(self, agent: ContextAgent) -> None:
        with pytest.raises(InputValidationError) as exc_info:
            agent.run({
                "distance_to_target": "not_a_number",
                "lie_type": "zzz_invalid",
            })
        assert len(exc_info.value.errors) >= 2
