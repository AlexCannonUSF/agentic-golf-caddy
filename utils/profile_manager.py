# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""File-based player profile CRUD utilities."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any

from models import PlayerProfile, SkillLevel


class ProfileNotFoundError(FileNotFoundError):
    """Raised when a requested profile cannot be found."""


class ProfileAlreadyExistsError(FileExistsError):
    """Raised when attempting to create a profile that already exists."""


def _slugify_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_")
    if not slug:
        raise ValueError("Profile name must include at least one alphanumeric character.")
    return slug


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


class ProfileManager:
    """Load, save, and manage player profiles stored as JSON files."""

    def __init__(
        self,
        profile_dir: str | Path | None = None,
        default_profiles_dir: str | Path | None = None,
    ) -> None:
        env_profile_dir = os.getenv("PROFILE_DIR")
        resolved_profile_dir = profile_dir or env_profile_dir or (_repo_root() / "profiles")
        self.profile_dir = Path(resolved_profile_dir)
        self.default_profiles_dir = Path(default_profiles_dir or (_repo_root() / "profiles"))
        # Profiles are plain JSON files so they are easy to inspect, edit, and
        # include in tests without a database.
        self.profile_dir.mkdir(parents=True, exist_ok=True)

    def _path_for_profile_name(self, profile_name: str) -> Path:
        slug = _slugify_name(profile_name.removesuffix(".json"))
        return self.profile_dir / f"{slug}.json"

    def _resolve_existing_path(self, profile_name: str) -> Path:
        raw = profile_name.strip()
        if not raw:
            raise ValueError("profile_name cannot be empty.")
        if Path(raw).name != raw:
            raise ValueError("profile_name must not include path separators.")

        direct_candidate = self.profile_dir / raw
        candidates = [direct_candidate]
        if direct_candidate.suffix != ".json":
            candidates.append(self.profile_dir / f"{raw}.json")
        candidates.append(self._path_for_profile_name(raw))

        # Accept either a stem like "default_intermediate" or a file name like
        # "default_intermediate.json" so the UI and tests can use friendly names.
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate

        raise ProfileNotFoundError(f"Profile '{profile_name}' was not found in {self.profile_dir}.")

    def _read_profile_file(self, path: Path) -> PlayerProfile:
        try:
            raw_json = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ProfileNotFoundError(f"Profile file not found: {path}") from exc

        try:
            payload: Any = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Profile file contains invalid JSON: {path}") from exc

        if isinstance(payload, dict):
            # JSON cannot contain real comments, so checked-in profile files use
            # a metadata field for the AI disclosure. Remove it before strict
            # PlayerProfile validation so the disclosure does not become app data.
            payload.pop("_ai_disclosure", None)

        try:
            return PlayerProfile.model_validate(payload)
        except Exception as exc:
            raise ValueError(f"Profile file failed schema validation: {path}") from exc

    def list_profiles(self) -> list[str]:
        """Return sorted profile names (file stems) in the active profile directory."""

        return sorted(path.stem for path in self.profile_dir.glob("*.json") if path.is_file())

    def save_profile(
        self,
        profile: PlayerProfile,
        *,
        overwrite: bool = True,
        file_name: str | None = None,
    ) -> Path:
        """Persist a profile to disk and return the saved path."""

        target_name = file_name or profile.name
        path = self._path_for_profile_name(target_name)

        if path.exists() and not overwrite:
            raise ProfileAlreadyExistsError(f"Profile '{path.stem}' already exists.")

        payload = profile.model_dump(mode="json")
        # Pydantic validates the profile before this point; writing JSON keeps
        # the saved profile portable and readable.
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def create_profile(self, profile: PlayerProfile, *, file_name: str | None = None) -> Path:
        """Create a new profile and fail if it already exists."""

        return self.save_profile(profile, overwrite=False, file_name=file_name)

    def load_profile(self, profile_name: str) -> PlayerProfile:
        """Load a profile from the active profile directory."""

        path = self._resolve_existing_path(profile_name)
        return self._read_profile_file(path)

    def update_profile(self, profile_name: str, **updates: Any) -> PlayerProfile:
        """Update an existing profile with partial fields and persist changes."""

        existing_path = self._resolve_existing_path(profile_name)
        existing_profile = self._read_profile_file(existing_path)

        merged = existing_profile.model_dump(mode="python")
        merged.update(updates)
        updated_profile = PlayerProfile.model_validate(merged)

        new_path = self.save_profile(updated_profile, overwrite=True, file_name=updated_profile.name)
        if new_path != existing_path and existing_path.exists():
            existing_path.unlink()

        return updated_profile

    def delete_profile(self, profile_name: str) -> None:
        """Delete a profile by name."""

        path = self._resolve_existing_path(profile_name)
        path.unlink()

    def load_default_profile(self, skill_level: SkillLevel | str) -> PlayerProfile:
        """Load one of the built-in default skill-level profiles."""

        normalized_level = SkillLevel(skill_level).value
        default_path = self.default_profiles_dir / f"default_{normalized_level}.json"
        if not default_path.exists():
            raise ProfileNotFoundError(f"Default profile does not exist: {default_path}")
        return self._read_profile_file(default_path)

    def bootstrap_default_profiles(self, *, overwrite: bool = False) -> list[Path]:
        """
        Copy built-in default profiles into the active profile directory.
        Returns the list of files created/overwritten.
        """

        copied_paths: list[Path] = []
        for level in SkillLevel:
            source = self.default_profiles_dir / f"default_{level.value}.json"
            if not source.exists():
                raise ProfileNotFoundError(f"Missing default profile: {source}")

            destination = self.profile_dir / source.name
            if destination.exists() and not overwrite:
                continue

            if source.resolve() != destination.resolve():
                shutil.copyfile(source, destination)
            copied_paths.append(destination)

        return copied_paths
