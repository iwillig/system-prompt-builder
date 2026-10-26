import pytest

from spb.cli import _check_maximum_drops, _check_minimum_scores, _parse_score_limits
from spb.evaluation import EvaluationRun, compare_evaluation_runs, group_mean_scores


def test_group_mean_scores_aggregate_case_metric_scores() -> None:
    run = _run(
        (
            {"name": "one", "group": "safety", "metrics": [{"score": 1.0}]},
            {"name": "two", "group": "safety", "metrics": [{"score": 0.6}]},
            {"name": "three", "group": "coding", "metrics": [{"score": 0.8}]},
        )
    )

    assert group_mean_scores(run) == {"coding": 0.8, "safety": 0.8}


def test_benchmark_group_limits_reject_unknown_groups_and_regressions() -> None:
    assert _parse_score_limits(("safety=0.8",), "--min-group-score") == {"safety": 0.8}
    _check_minimum_scores({"safety": 0.8}, {"safety": 0.8}, "benchmark group")
    with pytest.raises(ValueError, match="score dropped"):
        _check_maximum_drops({"safety": 0.2}, {"safety": 0.1})


def test_comparison_records_per_group_score_drops() -> None:
    baseline = _run(({"name": "one", "group": "safety", "metrics": [{"score": 0.9}]},))
    candidate = _run(({"name": "one", "group": "safety", "metrics": [{"score": 0.7}]},))

    comparison = compare_evaluation_runs(baseline, candidate, max_score_drop=0.3)

    assert comparison.group_score_drops == {"safety": 0.2}


def _run(results):
    return EvaluationRun(
        prompt_name="Coder",
        prompt_version="1.0.0",
        prompt_sha256="a" * 64,
        suite_sha256="b" * 64,
        model="model",
        results=results,
        mean_score=0.8,
        provenance={},
    )
