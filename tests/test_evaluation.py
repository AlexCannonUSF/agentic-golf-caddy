# AI disclosure: This file was written or edited with help from OpenAI Codex through Alex Cannon's prompts.
from evaluation import EvaluationRunner, load_adaptive_cases, load_clarification_cases, load_deterministic_cases


def test_benchmark_loaders_return_cases() -> None:
    assert len(load_deterministic_cases()) >= 1
    assert len(load_adaptive_cases()) >= 1
    assert len(load_clarification_cases()) >= 1


def test_evaluation_runner_preserves_or_improves_adaptive_accuracy(sample_profile) -> None:
    report = EvaluationRunner(sample_profile).run_all()

    adaptive_report = report["adaptive_scenarios"]
    clarification_report = report["clarification_scenarios"]

    assert adaptive_report["adaptive_lift"]["acceptable_set_accuracy"] >= 0.0
    assert adaptive_report["bounded_hybrid"]["acceptable_set_accuracy"] >= adaptive_report["deterministic_only"]["acceptable_set_accuracy"]
    assert clarification_report["clarification_precision"] >= 0.5
    assert report["failure_recovery"]["fallback_reliability"] == 1.0
