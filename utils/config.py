"""Shared configuration helpers for environment-aware integrations."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def project_root() -> Path:
    """Return the repository root."""

    return Path(__file__).resolve().parents[1]


def data_dir() -> Path:
    """Return the project data directory, creating it if needed."""

    path = project_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir(source: str) -> Path:
    """Return the cache directory for a given source."""

    path = data_dir() / "cache" / source
    path.mkdir(parents=True, exist_ok=True)
    return path


def nominatim_user_agent() -> str:
    """Return the configured User-Agent for Nominatim requests."""

    contact = os.getenv("NOMINATIM_CONTACT", "").strip()
    suffix = f" (contact: {contact})" if contact else ""
    return f"AgenticGolfCaddy/1.0{suffix}"


def http_timeout_seconds() -> float:
    """Return the default timeout used for data-source calls."""

    raw_value = os.getenv("HTTP_TIMEOUT_SECONDS", "8").strip()
    try:
        return max(1.0, float(raw_value))
    except ValueError:
        return 8.0

