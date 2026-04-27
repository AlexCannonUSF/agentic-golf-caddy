"""File-based course storage and lookup helpers."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from models import Course
from utils.config import data_dir


class CourseNotFoundError(FileNotFoundError):
    """Raised when a requested course file cannot be found."""


def _slugify_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_")
    if not slug:
        raise ValueError("Course id/name must include at least one alphanumeric character.")
    return slug


class CourseManager:
    """Persist and load normalized course JSON files under ``data/courses``."""

    def __init__(self, course_dir: str | Path | None = None) -> None:
        self.course_dir = Path(course_dir) if course_dir is not None else data_dir() / "courses"
        self.course_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.course_dir / "index.json"

    def _path_for_course_id(self, course_id: str) -> Path:
        return self.course_dir / f"{_slugify_name(course_id)}.json"

    def _resolve_existing_path(self, course_id: str) -> Path:
        raw = course_id.strip()
        if not raw:
            raise ValueError("course_id cannot be empty.")

        candidates = [
            self.course_dir / raw,
            self.course_dir / f"{raw}.json",
            self._path_for_course_id(raw.removesuffix(".json")),
        ]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        raise CourseNotFoundError(f"Course '{course_id}' was not found in {self.course_dir}.")

    def _read_course_file(self, path: Path) -> Course:
        try:
            payload: Any = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise CourseNotFoundError(f"Course file not found: {path}") from exc
        except json.JSONDecodeError as exc:
            raise ValueError(f"Course file contains invalid JSON: {path}") from exc

        try:
            return Course.model_validate(payload)
        except Exception as exc:
            raise ValueError(f"Course file failed schema validation: {path}") from exc

    def _write_index(self) -> None:
        records = []
        for path in sorted(self.course_dir.glob("*.json")):
            if path.name == "index.json":
                continue
            try:
                course = self._read_course_file(path)
            except Exception:
                continue
            records.append(
                {
                    "id": course.id,
                    "name": course.name,
                    "hole_count": len(course.holes),
                    "osm_ref": course.osm_ref,
                    "source": course.source,
                    "file_name": path.name,
                }
            )
        self._index_path.write_text(json.dumps(records, indent=2), encoding="utf-8")

    def list_courses(self) -> list[str]:
        """Return the sorted list of saved course ids."""

        return sorted(
            path.stem
            for path in self.course_dir.glob("*.json")
            if path.is_file() and path.name != "index.json"
        )

    def list_course_records(self) -> list[dict[str, Any]]:
        """Return structured metadata for all saved courses."""

        if not self._index_path.exists():
            self._write_index()
        try:
            payload = json.loads(self._index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            self._write_index()
            payload = json.loads(self._index_path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, list) else []

    def save_course(
        self,
        course: Course,
        *,
        overwrite: bool = True,
        file_name: str | None = None,
    ) -> Path:
        """Persist a normalized course and update ``index.json``."""

        target_name = file_name or course.id
        path = self._path_for_course_id(target_name)
        if path.exists() and not overwrite:
            raise FileExistsError(f"Course '{path.stem}' already exists.")

        path.write_text(
            json.dumps(course.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        self._write_index()
        return path

    def load_course(self, course_id: str) -> Course:
        """Load a saved course by id or file name."""

        return self._read_course_file(self._resolve_existing_path(course_id))
