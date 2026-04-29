"""Agent 1: Input/Context Agent — validates and normalizes raw shot input."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import date
from typing import Any

from models import Elevation, Hole, LatLon, PinPosition, ShotContext, TargetMode, WeatherObservation, WindDirection
from utils.course_manager import CourseManager
from utils.pin_manager import PinManager
from utils.data_sources import get_elevation, get_elevation_delta, get_weather
from utils.geometry import centroid, derive_pin_position, green_reference_points, haversine_yards, line_projection_metrics
from utils.logger import PipelineLogger
from utils.validators import InputValidationError, ValidationResult, validate_shot_input

logger = logging.getLogger(__name__)


class ContextAgent:
    """Validate raw user input and produce a clean ShotContext."""

    def __init__(
        self,
        *,
        course_manager: CourseManager | None = None,
        pin_manager: PinManager | None = None,
        pipeline_logger: PipelineLogger | None = None,
    ) -> None:
        self._course_manager = course_manager or CourseManager()
        self._pin_manager = pin_manager or PinManager()
        self._pipeline_logger = pipeline_logger

    @staticmethod
    def _coerce_location(value: Any) -> LatLon | None:
        if value in (None, ""):
            return None
        if isinstance(value, LatLon):
            return value
        if isinstance(value, (tuple, list)) and len(value) == 2:
            return LatLon(lat=value[0], lon=value[1])
        if isinstance(value, Mapping):
            return LatLon.model_validate(value)
        raise ValueError("Location must be a LatLon, (lat, lon), or {'lat','lon'} mapping.")

    @staticmethod
    def _coerce_optional_float(value: Any, field_name: str) -> float | None:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            raise ValueError(f"{field_name} must be numeric.")
        try:
            return float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be numeric.") from exc

    @staticmethod
    def _wind_direction_from_degrees(
        wind_direction_deg: float,
        shot_azimuth_deg: float,
    ) -> WindDirection:
        relative = ((wind_direction_deg - shot_azimuth_deg + 180.0) % 360.0) - 180.0
        if abs(relative) <= 45.0:
            return WindDirection.HEADWIND
        if abs(relative) >= 135.0:
            return WindDirection.TAILWIND
        return WindDirection.CROSSWIND_RIGHT if relative > 0 else WindDirection.CROSSWIND_LEFT

    @staticmethod
    def _elevation_enum_from_delta(delta_ft: float) -> Elevation:
        if abs(delta_ft) < 8.0:
            return Elevation.FLAT
        if delta_ft >= 20.0:
            return Elevation.STEEP_UPHILL
        if delta_ft > 0.0:
            return Elevation.UPHILL
        if delta_ft <= -20.0:
            return Elevation.STEEP_DOWNHILL
        return Elevation.DOWNHILL

    @staticmethod
    def _is_blank(mapping: Mapping[str, Any], field_name: str) -> bool:
        return field_name not in mapping or mapping.get(field_name) in (None, "")

    def _log_data_source(self, source_name: str, data: dict[str, Any]) -> None:
        if self._pipeline_logger is not None:
            self._pipeline_logger.log_data_source(source_name, data)

    @staticmethod
    def _coerce_optional_int(value: Any, field_name: str) -> int | None:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            raise ValueError(f"{field_name} must be numeric.")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be numeric.") from exc

    @staticmethod
    def _resolve_hole(course_id: str, hole_number: int, hole_candidates: list[Hole]) -> Hole:
        for hole in hole_candidates:
            if hole.number == hole_number:
                return hole
        raise ValueError(f"Course '{course_id}' does not contain hole {hole_number}.")

    def _resolve_tee_location(self, raw_input: Mapping[str, Any], hole: Hole) -> LatLon:
        tee_location = self._coerce_location(raw_input.get("tee_lat_lon"))
        if tee_location is not None:
            return tee_location

        tee_label = str(raw_input.get("tee_label", "")).strip().lower()
        if tee_label:
            for tee in hole.tees:
                if tee.label.lower() == tee_label or (tee.color or "").lower() == tee_label:
                    return tee.center

        if hole.tees:
            return hole.tees[0].center

        raise ValueError("Selected hole does not include any tee locations.")

    @staticmethod
    def _coerce_optional_date(value: Any, field_name: str) -> date | None:
        if value in (None, ""):
            return None
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value))
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an ISO date like YYYY-MM-DD.") from exc

    def _resolve_pin_lat_lon(
        self,
        raw_input: Mapping[str, Any],
        course_id: str,
        hole: Hole,
        tee_location: LatLon,
    ) -> tuple[LatLon | None, str | None]:
        explicit_pin = self._coerce_location(raw_input.get("pin_lat_lon"))
        if explicit_pin is not None:
            return explicit_pin, "explicit"

        pin_source = str(raw_input.get("pin_source", "")).strip().lower()
        pin_date = self._coerce_optional_date(raw_input.get("pin_date"), "pin_date")

        if pin_source not in {"none", "front", "middle", "back", "saved"}:
            pin_source = "saved"

        if pin_source == "none":
            return None, None

        if pin_source == "saved":
            saved_pin = self._pin_manager.get_pin(course_id, hole.number, pin_date)
            if saved_pin is not None:
                return saved_pin.pin_lat_lon, "saved"

        if pin_source in {"front", "middle", "back"}:
            preset = green_reference_points(hole.green.polygon, tee_location)
            return preset[PinPosition(pin_source)], pin_source

        pin_position_raw = str(raw_input.get("pin_position", "")).strip().lower()
        if pin_position_raw in {"front", "middle", "back"}:
            preset = green_reference_points(hole.green.polygon, tee_location)
            return preset[PinPosition(pin_position_raw)], pin_position_raw

        return None, None

    @staticmethod
    def _derive_hazard_note(tee_location: LatLon, target_location: LatLon, hole: Hole) -> str | None:
        if not hole.hazards:
            return None

        best_note: str | None = None
        best_score = float("inf")
        for hazard in hole.hazards:
            along_ratio, lateral_yards, side = line_projection_metrics(
                tee_location,
                target_location,
                hazard.center,
            )

            if along_ratio < 0.88 and lateral_yards <= 35.0:
                position = "short"
            elif along_ratio > 1.03 and lateral_yards <= 35.0:
                position = "long"
            elif side in {"left", "right"}:
                position = side
            else:
                position = "short" if along_ratio <= 1.0 else "long"

            position_penalty = abs(1.0 - along_ratio) * 25.0
            score = lateral_yards + position_penalty
            if score < best_score:
                best_score = score
                best_note = f"{hazard.kind}_{position}"

        return best_note

    @staticmethod
    def _derive_target_mode(target_location: LatLon, hole: Hole, hazard_note: str | None) -> TargetMode:
        if hazard_note and any(token in hazard_note for token in ("water", "ob", "trees")):
            return TargetMode.CENTER_GREEN

        for hazard in hole.hazards:
            if haversine_yards(hazard.center, target_location) <= 25.0:
                return TargetMode.CENTER_GREEN

        return TargetMode.PIN

    def _enrich_with_course_data(self, raw_input: Mapping[str, Any]) -> dict[str, Any]:
        enriched = dict(raw_input)
        course_id_raw = raw_input.get("course_id")
        hole_number_raw = raw_input.get("hole_number")
        if course_id_raw in (None, "") or hole_number_raw in (None, ""):
            return enriched

        course_id = str(course_id_raw).strip()
        hole_number = self._coerce_optional_int(hole_number_raw, "hole_number")
        if hole_number is None:
            return enriched

        course = self._course_manager.load_course(course_id)
        hole = self._resolve_hole(course_id, hole_number, course.holes)
        tee_location = self._resolve_tee_location(raw_input, hole)
        explicit_distance_provided = not self._is_blank(raw_input, "distance_to_target")
        green_center = hole.green.center
        target_location = green_center
        derived_distance = haversine_yards(tee_location, green_center)
        derived_target_mode = None
        pin_lat_lon, resolved_pin_source = self._resolve_pin_lat_lon(raw_input, course.id, hole, tee_location)

        if not explicit_distance_provided and derived_distance > 350.0:
            # Long holes often start from the tee but should not force the app
            # to recommend a max-distance club for every context. In that case,
            # derive a sensible layup target from the fairway geometry.
            fairway_target = centroid(hole.fairway_polygon)
            layup_distance = haversine_yards(tee_location, fairway_target)
            if 30.0 <= layup_distance <= 350.0:
                target_location = fairway_target
                derived_distance = layup_distance
                derived_target_mode = TargetMode.LAYUP

        if self._is_blank(raw_input, "location"):
            enriched["location"] = tee_location.model_dump(mode="json")

        if not explicit_distance_provided:
            enriched["distance_to_target"] = derived_distance
            enriched.setdefault("origin_lat_lon", tee_location.model_dump(mode="json"))
            if self._is_blank(raw_input, "target_location"):
                enriched["target_location"] = target_location.model_dump(mode="json")

        if pin_lat_lon is not None:
            enriched["pin_lat_lon"] = pin_lat_lon.model_dump(mode="json")
            enriched["pin_position"] = derive_pin_position(
                pin_lat_lon,
                hole.green.polygon,
                tee_location,
            ).value
            if (
                not explicit_distance_provided
                and derived_target_mode is None
                and str(raw_input.get("target_mode", "")).strip().lower() in {"", "pin"}
            ):
                pin_distance = haversine_yards(tee_location, pin_lat_lon)
                if 30.0 <= pin_distance <= 350.0:
                    enriched["distance_to_target"] = pin_distance
                    target_location = pin_lat_lon
                    if self._is_blank(raw_input, "target_location"):
                        enriched["target_location"] = pin_lat_lon.model_dump(mode="json")

        if not explicit_distance_provided and self._is_blank(raw_input, "hazard_note"):
            derived_hazard = self._derive_hazard_note(tee_location, target_location, hole)
            if derived_hazard:
                enriched["hazard_note"] = derived_hazard

        if not explicit_distance_provided and self._is_blank(raw_input, "target_mode"):
            if derived_target_mode is not None:
                enriched["target_mode"] = derived_target_mode.value
            else:
                enriched["target_mode"] = self._derive_target_mode(
                    target_location,
                    hole,
                    str(enriched.get("hazard_note", "")).strip() or None,
                ).value

        self._log_data_source(
            "saved_course",
            {
                "course_id": course.id,
                "hole_number": hole.number,
                "tee_lat_lon": tee_location.model_dump(mode="json"),
                "pin_source": resolved_pin_source,
                "mode": "distance_locked" if explicit_distance_provided else "derive_context",
            },
        )
        return enriched

    def _enrich_with_environment(self, raw_input: Mapping[str, Any]) -> dict[str, Any]:
        course_enriched = self._enrich_with_course_data(raw_input)
        explicit_distance_provided = not self._is_blank(raw_input, "distance_to_target")
        user_supplied_location = not self._is_blank(raw_input, "location")
        user_supplied_target = not self._is_blank(raw_input, "target_location")
        enriched = {
            key: value
            for key, value in course_enriched.items()
            if key not in {"weather_observation", "location", "target_location", "shot_azimuth_deg", "live_weather_requested", "live_elevation_requested"}
        }

        location = self._coerce_location(course_enriched.get("location"))
        target_location = self._coerce_location(course_enriched.get("target_location"))
        shot_azimuth_deg = self._coerce_optional_float(course_enriched.get("shot_azimuth_deg"), "shot_azimuth_deg")
        live_weather_requested = bool(course_enriched.get("live_weather_requested", False))
        live_elevation_requested = bool(course_enriched.get("live_elevation_requested", live_weather_requested))

        weather_observation = course_enriched.get("weather_observation")
        if weather_observation not in (None, "") and not isinstance(weather_observation, WeatherObservation):
            weather_observation = WeatherObservation.model_validate(weather_observation)

        if location is not None and weather_observation is None:
            weather_needs_fetch = live_weather_requested or any(
                self._is_blank(course_enriched, field_name)
                for field_name in ("wind_speed", "temperature")
            )
            if weather_needs_fetch:
                try:
                    weather_observation = get_weather(location.lat, location.lon)
                    self._log_data_source(
                        "open-meteo",
                        {
                            "lat": location.lat,
                            "lon": location.lon,
                            "mode": "fetch",
                        },
                    )
                except Exception:
                    logger.exception("ContextAgent: weather lookup failed, falling back to manual inputs")

        if weather_observation is not None:
            # Live weather only fills fields the user left blank, unless the UI
            # explicitly requested live conditions for this run.
            if live_weather_requested or self._is_blank(course_enriched, "wind_speed"):
                enriched["wind_speed"] = weather_observation.wind_speed_mph
            if live_weather_requested or self._is_blank(course_enriched, "temperature"):
                enriched["temperature"] = weather_observation.temperature_f
            if shot_azimuth_deg is not None and (
                live_weather_requested or self._is_blank(course_enriched, "wind_direction")
            ):
                enriched["wind_direction"] = self._wind_direction_from_degrees(
                    weather_observation.wind_direction_deg,
                    shot_azimuth_deg,
                ).value

        if location is not None:
            if not explicit_distance_provided:
                enriched.setdefault("origin_lat_lon", location.model_dump(mode="json"))
            altitude_needs_fetch = live_elevation_requested or self._is_blank(course_enriched, "altitude_ft")
            if altitude_needs_fetch:
                try:
                    enriched["altitude_ft"] = get_elevation(location.lat, location.lon)
                    self._log_data_source(
                        "usgs_epqs_altitude",
                        {"lat": location.lat, "lon": location.lon, "mode": "fetch"},
                    )
                except Exception:
                    logger.exception("ContextAgent: altitude lookup failed, falling back to manual altitude")

        should_derive_elevation_delta = (
            location is not None
            and target_location is not None
            and (
                not explicit_distance_provided
                or (user_supplied_location and user_supplied_target)
            )
        )
        if should_derive_elevation_delta:
            elevation_needs_fetch = live_elevation_requested or self._is_blank(course_enriched, "elevation")
            if elevation_needs_fetch:
                try:
                    elevation_delta_ft = get_elevation_delta(location, target_location)
                    enriched["elevation"] = self._elevation_enum_from_delta(elevation_delta_ft).value
                    self._log_data_source(
                        "usgs_epqs_elevation_delta",
                        {
                            "start": location.model_dump(mode="json"),
                            "end": target_location.model_dump(mode="json"),
                            "delta_ft": elevation_delta_ft,
                            "mode": "fetch",
                        },
                    )
                except Exception:
                    logger.exception("ContextAgent: elevation delta lookup failed, falling back to manual elevation")

        return enriched

    def run(self, raw_input: Mapping[str, Any]) -> ShotContext:
        """Validate *raw_input* and return a typed ShotContext.

        Raises ``InputValidationError`` when validation fails.
        """
        logger.info("ContextAgent: validating raw input")
        logger.debug("ContextAgent raw_input: %s", dict(raw_input))

        try:
            enriched_input = self._enrich_with_environment(raw_input)
        except ValueError as exc:
            raise InputValidationError([str(exc)]) from exc

        result: ValidationResult = validate_shot_input(enriched_input)

        if not result.is_valid or result.shot_context is None:
            logger.warning("ContextAgent: validation failed — %s", result.errors)
            raise InputValidationError(list(result.errors))

        logger.info("ContextAgent: produced ShotContext (distance=%.1f)", result.shot_context.distance_to_target)
        return result.shot_context
