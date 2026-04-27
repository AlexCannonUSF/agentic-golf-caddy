"""Input interpreter agent for natural-language shot descriptions."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Mapping

from models import CourseContext, PinPosition, ShotIntent, TargetMode, UserIntent

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_DEFAULT_PROMPT_FILE = _PROMPTS_DIR / "input_interpreter_prompt_v1.txt"

_SUPPORTED_FIELDS = {
    "distance_to_target",
    "lie_type",
    "wind_speed",
    "wind_direction",
    "elevation",
    "strategy",
    "temperature",
    "altitude_ft",
    "target_mode",
    "pin_position",
    "hazard_note",
    "player_confidence",
}


def _load_prompt_template(prompt_file: Path | None = None) -> str:
    path = prompt_file or _DEFAULT_PROMPT_FILE
    return path.read_text(encoding="utf-8")


def _extract_json_payload(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def _structured_input_to_intent(raw_input: Mapping[str, Any]) -> ShotIntent:
    parsed_fields = {key: value for key, value in raw_input.items() if key in _SUPPORTED_FIELDS and value is not None}
    field_confidence = {key: 1.0 for key in parsed_fields}
    course_context = CourseContext(
        target_mode=parsed_fields.get("target_mode", TargetMode.PIN.value),
        pin_position=parsed_fields.get("pin_position"),
        hazard_note=parsed_fields.get("hazard_note"),
    )
    return ShotIntent(
        raw_text="[structured_input]",
        parsed_fields=parsed_fields,
        field_confidence=field_confidence,
        missing_fields=[],
        ambiguous_fields=[],
        course_context=course_context,
        user_intent=UserIntent(goal=parsed_fields.get("strategy")),
        user_facing_summary="Structured input supplied directly.",
    )


def _detect_hazard(text: str) -> str | None:
    if "water" in text:
        if "short" in text:
            return "water_short"
        if "long" in text:
            return "water_long"
        if "left" in text:
            return "water_left"
        if "right" in text:
            return "water_right"
        return "water"
    if "bunker" in text and "lie" not in text:
        if "short" in text:
            return "bunker_short"
        if "long" in text:
            return "bunker_long"
        return "bunker_near_green"
    if "trouble left" in text or "trees left" in text or "left trouble" in text:
        return "trouble_left"
    if "trouble right" in text or "trees right" in text or "right trouble" in text:
        return "trouble_right"
    return None


def _build_summary(parsed_fields: dict[str, str | float | int | None]) -> str:
    distance = parsed_fields.get("distance_to_target")
    lie = parsed_fields.get("lie_type", "fairway")
    wind = parsed_fields.get("wind_speed")
    wind_dir = parsed_fields.get("wind_direction")
    target_mode = parsed_fields.get("target_mode", "pin")

    parts = []
    if distance is not None:
        parts.append(f"{float(distance):.0f} yards")
    parts.append(f"lie: {lie}")
    if wind is not None:
        parts.append(f"wind: {wind} mph {wind_dir or 'unknown direction'}")
    parts.append(f"target: {target_mode}")
    return ", ".join(parts)


def _heuristic_parse_shot_text(text: str) -> ShotIntent:
    lower_text = text.lower()
    parsed_fields: dict[str, str | float | int | None] = {}
    field_confidence: dict[str, float] = {}
    missing_fields: list[str] = []
    ambiguous_fields: list[str] = []

    distance_patterns = [
        r"(\d{2,3}(?:\.\d+)?)\s*(?:yd|yds|yard|yards)\b",
        r"(\d{2,3}(?:\.\d+)?)\s*out\b",
        r"(\d{2,3}(?:\.\d+)?)\s*to\s*(?:the\s*)?(?:pin|flag|green)\b",
    ]
    for pattern in distance_patterns:
        match = re.search(pattern, lower_text)
        if match:
            parsed_fields["distance_to_target"] = round(float(match.group(1)), 1)
            field_confidence["distance_to_target"] = 0.95
            break
    if "distance_to_target" not in parsed_fields:
        missing_fields.append("distance_to_target")

    range_match = re.search(r"(\d{1,2})\s*(?:-|to)\s*(\d{1,2})\s*(?:mph)?", lower_text)
    if range_match:
        low, high = float(range_match.group(1)), float(range_match.group(2))
        parsed_fields["wind_speed"] = round((low + high) / 2.0, 1)
        field_confidence["wind_speed"] = 0.55
        ambiguous_fields.append("wind_speed")
    else:
        wind_match = re.search(r"(\d{1,2}(?:\.\d+)?)\s*(?:mph)\b", lower_text)
        if wind_match:
            parsed_fields["wind_speed"] = round(float(wind_match.group(1)), 1)
            field_confidence["wind_speed"] = 0.9
        elif any(keyword in lower_text for keyword in ("breezy", "gusty", "windy")):
            parsed_fields["wind_speed"] = 12.0
            field_confidence["wind_speed"] = 0.45
            ambiguous_fields.append("wind_speed")

    if any(token in lower_text for token in ("into the wind", "into wind", "in my face", "headwind")):
        parsed_fields["wind_direction"] = "headwind"
        field_confidence["wind_direction"] = 0.95
    elif any(token in lower_text for token in ("downwind", "helping wind", "tailwind")):
        parsed_fields["wind_direction"] = "tailwind"
        field_confidence["wind_direction"] = 0.95
    elif "left to right" in lower_text:
        parsed_fields["wind_direction"] = "crosswind_left"
        field_confidence["wind_direction"] = 0.9
    elif "right to left" in lower_text:
        parsed_fields["wind_direction"] = "crosswind_right"
        field_confidence["wind_direction"] = 0.9

    if "deep rough" in lower_text:
        parsed_fields["lie_type"] = "deep_rough"
        field_confidence["lie_type"] = 0.95
    elif "rough" in lower_text:
        parsed_fields["lie_type"] = "rough"
        field_confidence["lie_type"] = 0.9
    elif "bunker" in lower_text or "sand" in lower_text:
        parsed_fields["lie_type"] = "bunker"
        field_confidence["lie_type"] = 0.95
    elif "tee" in lower_text:
        parsed_fields["lie_type"] = "tee"
        field_confidence["lie_type"] = 0.9
    elif "fairway" in lower_text:
        parsed_fields["lie_type"] = "fairway"
        field_confidence["lie_type"] = 0.9
    elif "sitting down" in lower_text:
        parsed_fields["lie_type"] = "rough"
        field_confidence["lie_type"] = 0.5
        ambiguous_fields.append("lie_type")

    if "steep uphill" in lower_text:
        parsed_fields["elevation"] = "steep_uphill"
        field_confidence["elevation"] = 0.95
    elif "uphill" in lower_text:
        parsed_fields["elevation"] = "uphill"
        field_confidence["elevation"] = 0.9
    elif "steep downhill" in lower_text:
        parsed_fields["elevation"] = "steep_downhill"
        field_confidence["elevation"] = 0.95
    elif "downhill" in lower_text:
        parsed_fields["elevation"] = "downhill"
        field_confidence["elevation"] = 0.9

    if any(token in lower_text for token in ("play it safe", "safe", "conservative")):
        parsed_fields["strategy"] = "safe"
        field_confidence["strategy"] = 0.9
    elif any(token in lower_text for token in ("attack", "aggressive", "go at it")):
        parsed_fields["strategy"] = "aggressive"
        field_confidence["strategy"] = 0.9
    elif "neutral" in lower_text:
        parsed_fields["strategy"] = "neutral"
        field_confidence["strategy"] = 0.8

    if "front pin" in lower_text:
        parsed_fields["pin_position"] = "front"
        field_confidence["pin_position"] = 0.95
    elif "back pin" in lower_text:
        parsed_fields["pin_position"] = "back"
        field_confidence["pin_position"] = 0.95
    elif "middle pin" in lower_text or "center pin" in lower_text:
        parsed_fields["pin_position"] = "middle"
        field_confidence["pin_position"] = 0.95

    goal = None
    if "middle of the green" in lower_text or "center of the green" in lower_text:
        parsed_fields["target_mode"] = "center_green"
        field_confidence["target_mode"] = 0.95
        goal = "middle_of_green"
    elif "lay up" in lower_text or "layup" in lower_text:
        parsed_fields["target_mode"] = "layup"
        field_confidence["target_mode"] = 0.95
        goal = "layup"
    elif "must carry" in lower_text:
        parsed_fields["target_mode"] = "pin"
        field_confidence["target_mode"] = 0.7
        goal = "must_carry"
    elif "pin" in lower_text or "flag" in lower_text:
        parsed_fields["target_mode"] = "pin"
        field_confidence["target_mode"] = 0.8

    hazard_note = _detect_hazard(lower_text)
    if hazard_note:
        parsed_fields["hazard_note"] = hazard_note
        field_confidence["hazard_note"] = 0.8

    temperature_match = re.search(r"(\d{2,3})\s*(?:f|°f)\b", lower_text)
    if temperature_match:
        parsed_fields["temperature"] = float(temperature_match.group(1))
        field_confidence["temperature"] = 0.95

    altitude_match = re.search(r"(\d{3,5})\s*(?:ft|feet)\b", lower_text)
    if altitude_match:
        parsed_fields["altitude_ft"] = float(altitude_match.group(1))
        field_confidence["altitude_ft"] = 0.95

    confidence_match = re.search(r"confidence\s*(\d)", lower_text)
    if confidence_match:
        parsed_fields["player_confidence"] = int(confidence_match.group(1))
        field_confidence["player_confidence"] = 0.8

    course_context = CourseContext(
        target_mode=parsed_fields.get("target_mode", TargetMode.PIN.value),
        pin_position=parsed_fields.get("pin_position"),
        hazard_note=parsed_fields.get("hazard_note"),
    )
    user_intent = UserIntent(goal=goal or parsed_fields.get("strategy"))

    return ShotIntent(
        raw_text=text,
        parsed_fields=parsed_fields,
        field_confidence=field_confidence,
        missing_fields=missing_fields,
        ambiguous_fields=sorted(set(ambiguous_fields)),
        course_context=course_context,
        user_intent=user_intent,
        user_facing_summary=_build_summary(parsed_fields),
    )


class InputInterpreterAgent:
    """Parse natural-language shot descriptions into structured intent."""

    def __init__(self, prompt_file: Path | None = None, model: str = "gpt-4o-mini") -> None:
        self._prompt_template = _load_prompt_template(prompt_file)
        self._model = model

    def _llm_parse(self, shot_text: str) -> ShotIntent:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or OpenAI is None:
            raise RuntimeError("OpenAI not available for input interpretation.")

        client = OpenAI(api_key=api_key)
        prompt = self._prompt_template.replace("{shot_text}", shot_text)
        response = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
        )
        response_text = response.choices[0].message.content or ""
        payload = _extract_json_payload(response_text)

        course_context = CourseContext.model_validate(payload.get("course_context", {}))
        user_intent = UserIntent.model_validate(payload.get("user_intent", {}))
        parsed_fields = {
            key: value for key, value in dict(payload.get("parsed_fields", {})).items() if key in _SUPPORTED_FIELDS
        }
        return ShotIntent(
            raw_text=shot_text,
            parsed_fields=parsed_fields,
            field_confidence=dict(payload.get("field_confidence", {})),
            missing_fields=list(payload.get("missing_fields", [])),
            ambiguous_fields=list(payload.get("ambiguous_fields", [])),
            course_context=course_context,
            user_intent=user_intent,
            user_facing_summary=str(payload.get("user_facing_summary", _build_summary(parsed_fields))),
        )

    def run(self, raw_input: Mapping[str, Any]) -> ShotIntent:
        """Interpret either structured input or a free-text shot description."""

        shot_text = str(raw_input.get("shot_text", "")).strip()
        if not shot_text:
            return _structured_input_to_intent(raw_input)

        logger.info("InputInterpreterAgent: parsing free-text shot")
        try:
            intent = self._llm_parse(shot_text)
            logger.info("InputInterpreterAgent: parsed with LLM")
            return intent
        except RuntimeError as exc:
            logger.info("InputInterpreterAgent: %s Falling back to heuristic parser.", exc)
            return _heuristic_parse_shot_text(shot_text)
        except Exception:
            logger.exception("InputInterpreterAgent: LLM parsing failed, using heuristic parser")
            return _heuristic_parse_shot_text(shot_text)
