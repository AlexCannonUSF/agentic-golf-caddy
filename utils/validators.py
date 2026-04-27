"""Validation and normalization helpers for raw shot inputs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import get_close_matches
from typing import Any, Mapping

from pydantic import ValidationError

from models import Elevation, LatLon, LieType, PinPosition, ShotContext, Strategy, TargetMode, WindDirection

_LIE_VALUES = {item.value for item in LieType}
_WIND_VALUES = {item.value for item in WindDirection}
_ELEVATION_VALUES = {item.value for item in Elevation}
_STRATEGY_VALUES = {item.value for item in Strategy}
_TARGET_MODE_VALUES = {item.value for item in TargetMode}
_PIN_POSITION_VALUES = {item.value for item in PinPosition}

_LIE_ALIASES = {
    "tee_box": "tee",
    "teeing_ground": "tee",
    "sand": "bunker",
    "sand_trap": "bunker",
    "heavy_rough": "deep_rough",
    "thick_rough": "deep_rough",
    "first_cut": "rough",
}

_WIND_ALIASES = {
    "into": "headwind",
    "against": "headwind",
    "downwind": "tailwind",
    "helping": "tailwind",
    "left_to_right": "crosswind_left",
    "ltr": "crosswind_left",
    "right_to_left": "crosswind_right",
    "rtl": "crosswind_right",
}

_ELEVATION_ALIASES = {
    "up": "uphill",
    "down": "downhill",
    "steep_uphill": "steep_uphill",
    "steep_up": "steep_uphill",
    "steep_downhill": "steep_downhill",
    "steep_down": "steep_downhill",
}

_STRATEGY_ALIASES = {
    "standard": "neutral",
    "normal": "neutral",
    "attack": "aggressive",
    "conservative": "safe",
}

_TARGET_MODE_ALIASES = {
    "center": "center_green",
    "middle": "center_green",
    "middle_green": "center_green",
    "flag": "pin",
}

_PIN_POSITION_ALIASES = {
    "center": "middle",
    "middle_green": "middle",
}


@dataclass(frozen=True)
class ValidationResult:
    """Result object for shot input validation."""

    shot_context: ShotContext | None
    errors: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return self.shot_context is not None and not self.errors


class InputValidationError(ValueError):
    """Raised when shot input cannot be validated into ShotContext."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("Invalid shot input: " + " | ".join(errors))
        self.errors = tuple(errors)


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower().strip()).strip("_")


def _enum_error(field_name: str, raw_value: Any, allowed_values: set[str], aliases: dict[str, str]) -> str:
    candidates = sorted(allowed_values | set(aliases))
    normalized = _normalize_token(str(raw_value))
    suggested = get_close_matches(normalized, candidates, n=3, cutoff=0.45)
    allowed_text = ", ".join(sorted(allowed_values))

    if suggested:
        suggestion_text = ", ".join(suggested)
        return (
            f"{field_name} must be one of: {allowed_text}. "
            f"Got '{raw_value}'. Did you mean: {suggestion_text}?"
        )
    return f"{field_name} must be one of: {allowed_text}. Got '{raw_value}'."


def _normalize_enum(
    raw_value: Any,
    *,
    field_name: str,
    default: str,
    allowed_values: set[str],
    aliases: dict[str, str],
) -> tuple[str | None, str | None]:
    if raw_value is None or str(raw_value).strip() == "":
        return default, None

    normalized = _normalize_token(str(raw_value))
    if normalized in allowed_values:
        return normalized, None

    if normalized in aliases:
        return aliases[normalized], None

    fuzzy_candidates = sorted(allowed_values | set(aliases))
    close = get_close_matches(normalized, fuzzy_candidates, n=1, cutoff=0.74)
    if close:
        best_match = close[0]
        return aliases.get(best_match, best_match), None

    return None, _enum_error(field_name, raw_value, allowed_values, aliases)


def normalize_lie_type(raw_value: Any) -> str:
    value, error = _normalize_enum(
        raw_value,
        field_name="lie_type",
        default=LieType.FAIRWAY.value,
        allowed_values=_LIE_VALUES,
        aliases=_LIE_ALIASES,
    )
    if error:
        raise ValueError(error)
    return value or LieType.FAIRWAY.value


def normalize_wind_direction(raw_value: Any) -> str:
    value, error = _normalize_enum(
        raw_value,
        field_name="wind_direction",
        default=WindDirection.HEADWIND.value,
        allowed_values=_WIND_VALUES,
        aliases=_WIND_ALIASES,
    )
    if error:
        raise ValueError(error)
    return value or WindDirection.HEADWIND.value


def normalize_elevation(raw_value: Any) -> str:
    value, error = _normalize_enum(
        raw_value,
        field_name="elevation",
        default=Elevation.FLAT.value,
        allowed_values=_ELEVATION_VALUES,
        aliases=_ELEVATION_ALIASES,
    )
    if error:
        raise ValueError(error)
    return value or Elevation.FLAT.value


def normalize_strategy(raw_value: Any) -> str:
    value, error = _normalize_enum(
        raw_value,
        field_name="strategy",
        default=Strategy.NEUTRAL.value,
        allowed_values=_STRATEGY_VALUES,
        aliases=_STRATEGY_ALIASES,
    )
    if error:
        raise ValueError(error)
    return value or Strategy.NEUTRAL.value


def normalize_target_mode(raw_value: Any) -> str:
    value, error = _normalize_enum(
        raw_value,
        field_name="target_mode",
        default=TargetMode.PIN.value,
        allowed_values=_TARGET_MODE_VALUES,
        aliases=_TARGET_MODE_ALIASES,
    )
    if error:
        raise ValueError(error)
    return value or TargetMode.PIN.value


def normalize_pin_position(raw_value: Any) -> str | None:
    if raw_value is None or str(raw_value).strip() == "":
        return None
    value, error = _normalize_enum(
        raw_value,
        field_name="pin_position",
        default=PinPosition.MIDDLE.value,
        allowed_values=_PIN_POSITION_VALUES,
        aliases=_PIN_POSITION_ALIASES,
    )
    if error:
        raise ValueError(error)
    return value


def _parse_numeric(raw_value: Any, field_name: str) -> tuple[float | None, str | None]:
    if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
        return None, f"{field_name} is required."

    if isinstance(raw_value, bool):
        return None, f"{field_name} must be numeric."

    try:
        return float(raw_value), None
    except (TypeError, ValueError):
        return None, f"{field_name} must be numeric."


def _parse_location(raw_value: Any, field_name: str) -> tuple[dict[str, float] | None, str | None]:
    if raw_value is None or raw_value == "":
        return None, None
    try:
        location = LatLon.model_validate(raw_value)
    except Exception:
        return None, f"{field_name} must be a mapping with numeric lat/lon values."
    return location.model_dump(mode="json"), None


def validate_shot_input(raw_input: Mapping[str, Any]) -> ValidationResult:
    """Validate raw shot form payload and return typed ShotContext or errors."""

    cleaned: dict[str, Any] = {}
    errors: list[str] = []

    distance_raw = raw_input.get("distance_to_target", raw_input.get("distance"))
    distance, distance_error = _parse_numeric(distance_raw, "distance_to_target")
    if distance_error:
        errors.append(distance_error)
    elif distance is not None:
        if not 30.0 <= distance <= 350.0:
            errors.append("distance_to_target must be between 30 and 350 yards.")
        else:
            cleaned["distance_to_target"] = round(distance, 1)

    lie_value, lie_error = _normalize_enum(
        raw_input.get("lie_type"),
        field_name="lie_type",
        default=LieType.FAIRWAY.value,
        allowed_values=_LIE_VALUES,
        aliases=_LIE_ALIASES,
    )
    if lie_error:
        errors.append(lie_error)
    else:
        cleaned["lie_type"] = lie_value

    wind_speed, wind_error = _parse_numeric(raw_input.get("wind_speed", 0.0), "wind_speed")
    if wind_error:
        errors.append(wind_error)
    elif wind_speed is not None:
        cleaned["wind_speed"] = round(max(0.0, min(40.0, wind_speed)), 1)

    wind_direction, wind_direction_error = _normalize_enum(
        raw_input.get("wind_direction"),
        field_name="wind_direction",
        default=WindDirection.HEADWIND.value,
        allowed_values=_WIND_VALUES,
        aliases=_WIND_ALIASES,
    )
    if wind_direction_error:
        errors.append(wind_direction_error)
    else:
        cleaned["wind_direction"] = wind_direction

    elevation, elevation_error = _normalize_enum(
        raw_input.get("elevation"),
        field_name="elevation",
        default=Elevation.FLAT.value,
        allowed_values=_ELEVATION_VALUES,
        aliases=_ELEVATION_ALIASES,
    )
    if elevation_error:
        errors.append(elevation_error)
    else:
        cleaned["elevation"] = elevation

    strategy, strategy_error = _normalize_enum(
        raw_input.get("strategy"),
        field_name="strategy",
        default=Strategy.NEUTRAL.value,
        allowed_values=_STRATEGY_VALUES,
        aliases=_STRATEGY_ALIASES,
    )
    if strategy_error:
        errors.append(strategy_error)
    else:
        cleaned["strategy"] = strategy

    temperature, temperature_error = _parse_numeric(raw_input.get("temperature", 72.0), "temperature")
    if temperature_error:
        errors.append(temperature_error)
    elif temperature is not None:
        if not 20.0 <= temperature <= 120.0:
            errors.append("temperature must be between 20 and 120 Fahrenheit.")
        else:
            cleaned["temperature"] = round(temperature, 1)

    altitude, altitude_error = _parse_numeric(raw_input.get("altitude_ft", 0.0), "altitude_ft")
    if altitude_error:
        errors.append(altitude_error)
    elif altitude is not None:
        if not 0.0 <= altitude <= 10000.0:
            errors.append("altitude_ft must be between 0 and 10000.")
        else:
            cleaned["altitude_ft"] = round(altitude, 1)

    target_mode, target_mode_error = _normalize_enum(
        raw_input.get("target_mode"),
        field_name="target_mode",
        default=TargetMode.PIN.value,
        allowed_values=_TARGET_MODE_VALUES,
        aliases=_TARGET_MODE_ALIASES,
    )
    if target_mode_error:
        errors.append(target_mode_error)
    else:
        cleaned["target_mode"] = target_mode

    pin_position_raw = raw_input.get("pin_position")
    if pin_position_raw is not None and str(pin_position_raw).strip() != "":
        pin_position, pin_position_error = _normalize_enum(
            pin_position_raw,
            field_name="pin_position",
            default=PinPosition.MIDDLE.value,
            allowed_values=_PIN_POSITION_VALUES,
            aliases=_PIN_POSITION_ALIASES,
        )
        if pin_position_error:
            errors.append(pin_position_error)
        else:
            cleaned["pin_position"] = pin_position

    origin_lat_lon, origin_error = _parse_location(raw_input.get("origin_lat_lon"), "origin_lat_lon")
    if origin_error:
        errors.append(origin_error)
    elif origin_lat_lon is not None:
        cleaned["origin_lat_lon"] = origin_lat_lon

    pin_lat_lon, pin_error = _parse_location(raw_input.get("pin_lat_lon"), "pin_lat_lon")
    if pin_error:
        errors.append(pin_error)
    elif pin_lat_lon is not None:
        cleaned["pin_lat_lon"] = pin_lat_lon

    hazard_note = raw_input.get("hazard_note")
    if hazard_note is not None:
        cleaned["hazard_note"] = str(hazard_note).strip() or None

    player_confidence_raw = raw_input.get("player_confidence")
    if player_confidence_raw is not None and str(player_confidence_raw).strip() != "":
        player_confidence, player_confidence_error = _parse_numeric(
            player_confidence_raw,
            "player_confidence",
        )
        if player_confidence_error:
            errors.append(player_confidence_error)
        elif player_confidence is not None:
            if not 1.0 <= player_confidence <= 5.0:
                errors.append("player_confidence must be between 1 and 5.")
            else:
                cleaned["player_confidence"] = int(round(player_confidence))

    if errors:
        return ValidationResult(shot_context=None, errors=tuple(errors))

    try:
        context = ShotContext.model_validate(cleaned)
    except ValidationError as exc:
        model_errors = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"])
            model_errors.append(f"{location}: {error['msg']}")
        return ValidationResult(shot_context=None, errors=tuple(model_errors))

    return ValidationResult(shot_context=context, errors=tuple())


def validate_shot_context_or_raise(raw_input: Mapping[str, Any]) -> ShotContext:
    """Validate input and raise a rich exception on any issues."""

    result = validate_shot_input(raw_input)
    if not result.is_valid or result.shot_context is None:
        raise InputValidationError(list(result.errors))
    return result.shot_context
