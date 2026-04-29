# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
"""Persistence and summarization helpers for shot feedback history."""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from models import PlayerProfile, PlayerTendencies, ShotFeedback, ShotOutcome


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


class FeedbackManager:
    """Store shot feedback locally and derive lightweight player tendencies."""

    def __init__(self, feedback_file: str | Path | None = None) -> None:
        default_file = _repo_root() / "data" / "shot_feedback.json"
        self.feedback_file = Path(feedback_file or os.getenv("FEEDBACK_FILE") or default_file)
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_all(self) -> dict[str, list[dict[str, Any]]]:
        if not self.feedback_file.exists():
            return {}
        try:
            return json.loads(self.feedback_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write_all(self, payload: dict[str, list[dict[str, Any]]]) -> None:
        self.feedback_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add_feedback(self, profile_name: str, feedback: ShotFeedback) -> None:
        """Append feedback for the given profile."""

        payload = self._load_all()
        entries = payload.setdefault(profile_name, [])
        entries.append(feedback.model_dump(mode="json"))
        self._write_all(payload)

    def load_feedback(self, profile_name: str) -> list[ShotFeedback]:
        """Return feedback history for the given profile."""

        payload = self._load_all()
        return [ShotFeedback.model_validate(item) for item in payload.get(profile_name, [])]

    def load_all_feedback(self) -> list[ShotFeedback]:
        """Return all stored feedback entries across every profile."""

        payload = self._load_all()
        items: list[ShotFeedback] = []
        for entries in payload.values():
            items.extend(ShotFeedback.model_validate(item) for item in entries)
        return items

    def summarize_tendencies(self, profile: PlayerProfile) -> PlayerTendencies:
        """Build basic tendencies from persisted feedback and profile defaults."""

        feedback_items = self.load_feedback(profile.name)
        if not feedback_items:
            return profile.tendencies

        # Feedback is intentionally lightweight: each outcome nudges common miss,
        # confidence by club, and rough dispersion estimates for future runs.
        outcome_counter: Counter[str] = Counter()
        club_total: defaultdict[str, int] = defaultdict(int)
        club_miss_total: defaultdict[str, int] = defaultdict(int)

        for item in feedback_items:
            outcome_counter[item.outcome.value] += 1
            club_total[item.club_used] += 1
            if item.outcome != ShotOutcome.ON_TARGET:
                club_miss_total[item.club_used] += 1

        miss_candidates = {
            outcome: count
            for outcome, count in outcome_counter.items()
            if outcome not in {ShotOutcome.ON_TARGET.value, ShotOutcome.GOOD_CONTACT.value}
        }
        common_miss = max(miss_candidates, key=miss_candidates.get) if miss_candidates else None

        confidence_by_club: dict[str, float] = {}
        dispersion_by_club: dict[str, float] = {}
        for club_name, total in club_total.items():
            # A higher miss rate lowers confidence and increases dispersion, so
            # adaptive strategy can become more conservative with that club.
            miss_rate = club_miss_total[club_name] / total
            confidence_by_club[club_name] = round(max(0.1, 1.0 - miss_rate), 2)
            dispersion_by_club[club_name] = round(5.0 + (miss_rate * 20.0), 1)

        return PlayerTendencies(
            common_miss=common_miss or profile.tendencies.common_miss,
            shot_shape=profile.tendencies.shot_shape or profile.preferred_shot,
            confidence_by_club=confidence_by_club or profile.tendencies.confidence_by_club,
            dispersion_by_club=dispersion_by_club or profile.tendencies.dispersion_by_club,
        )
