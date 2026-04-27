"""Persist and hydrate real pipeline runs for offline evaluation."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from models import (
    AdaptiveDecision,
    CaddyDecision,
    ClarificationResult,
    Explanation,
    PlayerProfile,
    RunRecord,
    ShotContext,
    ShotFeedback,
    ShotIntent,
    VerificationResult,
)
from utils.config import project_root
from utils.feedback_manager import FeedbackManager


def _slugify_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower().strip()).strip("_")
    return slug or "unknown_player"


def _json_safe(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        timestamp = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(timezone.utc).isoformat()
    return value


class RunRecorder:
    """Append pipeline executions to ``data/evaluation/runs.jsonl``."""

    def __init__(self, runs_file: str | Path | None = None) -> None:
        default_file = project_root() / "data" / "evaluation" / "runs.jsonl"
        self.runs_file = Path(runs_file or default_file)
        self.runs_file.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def new_run_id() -> str:
        return uuid4().hex

    def append_record(self, record: RunRecord) -> None:
        with self.runs_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.model_dump(mode="json"), default=str))
            handle.write("\n")

    def record_pipeline_result(
        self,
        *,
        run_id: str,
        raw_input: dict[str, Any],
        player_profile: PlayerProfile,
        shot_intent: ShotIntent | None = None,
        clarification: ClarificationResult | None = None,
        shot_context: ShotContext | None = None,
        decision: CaddyDecision | None = None,
        adaptive_decision: AdaptiveDecision | None = None,
        explanation: Explanation | None = None,
        verification: VerificationResult | None = None,
        timing_seconds: dict[str, float] | None = None,
    ) -> RunRecord:
        status = "clarification_required" if clarification and clarification.needs_clarification else "completed"
        record = RunRecord(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc),
            status=status,
            raw_input=_json_safe(raw_input),
            shot_intent=shot_intent,
            clarification=clarification,
            shot_context=shot_context,
            decision=decision,
            adaptive_decision=adaptive_decision,
            explanation=explanation,
            explanation_summary=explanation.summary if explanation is not None else None,
            verification=verification,
            player_id=_slugify_name(player_profile.name),
            profile_name=player_profile.name,
            latency_ms={
                key: round(float(elapsed_seconds) * 1000.0, 1)
                for key, elapsed_seconds in (timing_seconds or {}).items()
            },
        )
        self.append_record(record)
        return record

    def _load_feedback_map(self, feedback_file: str | Path | None = None) -> dict[str, ShotFeedback]:
        manager = FeedbackManager(feedback_file)
        feedback_by_run_id: dict[str, ShotFeedback] = {}
        for feedback in manager.load_all_feedback():
            if feedback.run_id:
                feedback_by_run_id[feedback.run_id] = feedback
        return feedback_by_run_id

    def load_records(
        self,
        *,
        feedback_file: str | Path | None = None,
        player_id: str | None = None,
        profile_name: str | None = None,
    ) -> list[RunRecord]:
        if not self.runs_file.exists():
            return []

        feedback_by_run_id = self._load_feedback_map(feedback_file)
        records: list[RunRecord] = []
        for raw_line in self.runs_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            record = RunRecord.model_validate(payload)
            hydrated_outcome = feedback_by_run_id.get(record.run_id)
            if hydrated_outcome is not None:
                record = record.model_copy(update={"outcome": hydrated_outcome})
            if player_id and record.player_id != player_id:
                continue
            if profile_name and record.profile_name != profile_name:
                continue
            records.append(record)
        return sorted(records, key=lambda item: item.timestamp)

    @staticmethod
    def promotable_records(records: list[RunRecord]) -> list[RunRecord]:
        eligible: list[RunRecord] = []
        for record in records:
            if record.decision is None or record.outcome is None or record.outcome.recommendation_rating is None:
                continue
            eligible.append(record)
        return eligible

    def export_promoted_benchmarks(
        self,
        *,
        output_path: str | Path | None = None,
        feedback_file: str | Path | None = None,
        player_id: str | None = None,
        profile_name: str | None = None,
    ) -> Path:
        destination = Path(output_path or (project_root() / "benchmarks" / "real_shots.json"))
        destination.parent.mkdir(parents=True, exist_ok=True)

        promoted_payload: list[dict[str, Any]] = []
        for record in self.promotable_records(
            self.load_records(feedback_file=feedback_file, player_id=player_id, profile_name=profile_name)
        ):
            acceptable_clubs = [record.outcome.club_used]
            if record.outcome.recommendation_rating.value == "good_call":
                acceptable_clubs = list(dict.fromkeys([
                    record.outcome.club_used,
                    record.decision.primary_club,
                    record.decision.backup_club,
                ]))

            promoted_payload.append(
                {
                    "case_id": record.run_id,
                    "raw_input": _json_safe(record.raw_input),
                    "expected_club": record.outcome.club_used,
                    "acceptable_clubs": acceptable_clubs,
                    "expected_plays_like_distance": record.decision.plays_like_distance,
                    "tags": [
                        "real_shot",
                        record.player_id or "unknown_player",
                        record.outcome.recommendation_rating.value,
                    ],
                    "feedback_history": [record.outcome.model_dump(mode="json")],
                    "metadata": {
                        "recommended_primary_club": record.decision.primary_club,
                        "recommended_backup_club": record.decision.backup_club,
                        "confidence": record.decision.confidence.value,
                        "outcome": record.outcome.outcome.value,
                    },
                }
            )

        destination.write_text(json.dumps(promoted_payload, indent=2), encoding="utf-8")
        return destination
