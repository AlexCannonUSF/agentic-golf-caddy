# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Shared helpers for shot-history CSV importers."""

from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from pathlib import Path

from models import LieType
from utils.validators import normalize_lie_type


def normalize_header(header: str) -> str:
    """Normalize a CSV header into a lookup-friendly token."""

    return re.sub(r"[^a-z0-9]+", "_", header.lower().strip()).strip("_")


def read_csv_rows(data: bytes | str) -> tuple[list[dict[str, str]], list[str]]:
    """Read CSV bytes/text into normalized row dictionaries."""

    text = data.decode("utf-8-sig") if isinstance(data, bytes) else data
    # Some checked-in fixtures include a short attribution comment before the
    # CSV header. Skipping comment lines keeps the importer useful for normal
    # CSV exports while preserving the disclosure required for this project.
    csv_text = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    reader = csv.DictReader(io.StringIO(csv_text))
    fieldnames = [field or "" for field in (reader.fieldnames or [])]
    rows: list[dict[str, str]] = []

    for row in reader:
        normalized_row: dict[str, str] = {}
        for key, value in row.items():
            if key is None:
                continue
            normalized_row[normalize_header(key)] = (value or "").strip()
        if any(value for value in normalized_row.values()):
            rows.append(normalized_row)

    return rows, fieldnames


def first_present(row: dict[str, str], *candidate_keys: str) -> str | None:
    """Return the first non-empty value among normalized candidate keys."""

    for key in candidate_keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def parse_optional_float(value: str | None) -> float | None:
    """Parse an optional numeric string."""

    if value in (None, ""):
        return None
    return float(value.replace(",", ""))


def parse_optional_lie(value: str | None) -> LieType | None:
    """Parse an optional lie token."""

    if value in (None, ""):
        return None
    return LieType(normalize_lie_type(value))


def parse_timestamp(value: str | None) -> datetime:
    """Parse common timestamp formats used by shot exports."""

    if value in (None, ""):
        return datetime.now(timezone.utc)

    cleaned = value.strip()
    candidates = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
    ]
    try:
        parsed = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    for fmt in candidates:
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    raise ValueError(f"Unsupported timestamp format: {cleaned}")


def slugify_player_id(raw_value: str) -> str:
    """Return a filesystem-safe player slug."""

    slug = re.sub(r"[^a-z0-9]+", "_", raw_value.lower().strip()).strip("_")
    if not slug:
        raise ValueError("Player name/id must include at least one alphanumeric character.")
    return slug


def default_player_name(source_name: str | Path) -> str:
    """Return a player-like fallback name from a source filename."""

    stem = Path(source_name).stem
    parts = [part for part in re.split(r"[_\-\s]+", stem) if part]
    return " ".join(part.capitalize() for part in parts) or "Imported Player"
