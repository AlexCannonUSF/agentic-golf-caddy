"""Evaluate recorded real-world recommendation runs and emit a markdown report."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.real_runs import render_real_run_report, summarize_real_runs
from utils.evaluation import RunRecorder


def build_report(
    *,
    runs_file: str | Path | None = None,
    feedback_file: str | Path | None = None,
    player_id: str | None = None,
    profile_name: str | None = None,
) -> str:
    recorder = RunRecorder(runs_file)
    records = recorder.load_records(
        feedback_file=feedback_file,
        player_id=player_id,
        profile_name=profile_name,
    )
    summary = summarize_real_runs(records)
    return render_real_run_report(summary)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate real recorded Agentic Golf Caddy runs.")
    parser.add_argument("--runs-file", default=None, help="Optional path to runs.jsonl")
    parser.add_argument("--feedback-file", default=None, help="Optional path to shot_feedback.json")
    parser.add_argument("--player-id", default=None, help="Filter to one player id")
    parser.add_argument("--profile-name", default=None, help="Filter to one profile name")
    parser.add_argument("--output", default=None, help="Optional markdown output path")
    parser.add_argument(
        "--export-benchmarks",
        action="store_true",
        help="Also export promotable real-shot benchmark cases.",
    )
    parser.add_argument(
        "--benchmarks-output",
        default=None,
        help="Optional output path for promoted real-shot benchmarks JSON.",
    )
    args = parser.parse_args()

    report = build_report(
        runs_file=args.runs_file,
        feedback_file=args.feedback_file,
        player_id=args.player_id,
        profile_name=args.profile_name,
    )

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
    else:
        print(report)

    if args.export_benchmarks:
        recorder = RunRecorder(args.runs_file)
        exported_path = recorder.export_promoted_benchmarks(
            output_path=args.benchmarks_output,
            feedback_file=args.feedback_file,
            player_id=args.player_id,
            profile_name=args.profile_name,
        )
        print(f"\nPromoted benchmark cases written to {exported_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
