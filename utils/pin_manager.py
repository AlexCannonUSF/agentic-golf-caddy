"""File-based storage for daily course pin placements."""

from __future__ import annotations

import json
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from models import DailyPinSheet, HolePin, LatLon
from utils.config import data_dir


class PinSheetNotFoundError(FileNotFoundError):
    """Raised when a requested daily pin sheet does not exist."""


def _slugify_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_")
    if not slug:
        raise ValueError("Course id must include at least one alphanumeric character.")
    return slug


def _coerce_pin_date(pin_date: date | str | None) -> date:
    if pin_date is None:
        return date.today()
    if isinstance(pin_date, date):
        return pin_date
    return date.fromisoformat(str(pin_date))


class PinManager:
    """Persist and load daily pin sheets under ``data/pins/<course_id>/``."""

    def __init__(self, pin_dir: str | Path | None = None) -> None:
        self.pin_dir = Path(pin_dir) if pin_dir is not None else data_dir() / "pins"
        self.pin_dir.mkdir(parents=True, exist_ok=True)

    def _course_dir(self, course_id: str) -> Path:
        path = self.pin_dir / _slugify_name(course_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _path_for_sheet(self, course_id: str, pin_date: date | str | None) -> Path:
        resolved_date = _coerce_pin_date(pin_date)
        return self._course_dir(course_id) / f"{resolved_date.isoformat()}.json"

    def _read_sheet_file(self, path: Path) -> DailyPinSheet:
        try:
            payload: Any = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise PinSheetNotFoundError(f"Pin sheet not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Pin sheet contains invalid JSON: {path}") from exc

        try:
            return DailyPinSheet.model_validate(payload)
        except Exception as exc:
            raise ValueError(f"Pin sheet failed schema validation: {path}") from exc

    def load_sheet(self, course_id: str, pin_date: date | str | None = None) -> DailyPinSheet:
        """Load a daily pin sheet for the requested course/date."""

        return self._read_sheet_file(self._path_for_sheet(course_id, pin_date))

    def get_pin(
        self,
        course_id: str,
        hole_number: int,
        pin_date: date | str | None = None,
    ) -> HolePin | None:
        """Return the saved pin for one hole/date, if present."""

        try:
            sheet = self.load_sheet(course_id, pin_date)
        except PinSheetNotFoundError:
            return None

        for hole_pin in sheet.holes:
            if hole_pin.hole_number == hole_number:
                return hole_pin
        return None

    def save_pin(
        self,
        course_id: str,
        hole_number: int,
        pin_lat_lon: LatLon,
        *,
        pin_date: date | str | None = None,
        source: str = "manual",
    ) -> Path:
        """Save or update one hole pin in the daily sheet."""

        resolved_date = _coerce_pin_date(pin_date)
        path = self._path_for_sheet(course_id, resolved_date)

        try:
            existing = self.load_sheet(course_id, resolved_date)
            holes = list(existing.holes)
        except PinSheetNotFoundError:
            holes = []

        updated_pin = HolePin(
            hole_number=hole_number,
            pin_lat_lon=pin_lat_lon,
            source="saved" if source == "saved" else ("preset" if source == "preset" else "manual"),
            updated_at=datetime.now(timezone.utc),
        )

        replaced = False
        next_holes: list[HolePin] = []
        for hole_pin in holes:
            if hole_pin.hole_number == hole_number:
                next_holes.append(updated_pin)
                replaced = True
            else:
                next_holes.append(hole_pin)
        if not replaced:
            next_holes.append(updated_pin)

        next_holes.sort(key=lambda item: item.hole_number)
        sheet = DailyPinSheet(course_id=_slugify_name(course_id), pin_date=resolved_date, holes=next_holes)
        path.write_text(json.dumps(sheet.model_dump(mode="json"), indent=2), encoding="utf-8")
        return path
