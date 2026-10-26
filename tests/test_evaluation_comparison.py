import yaml

from spb.evaluation import (
    EvaluationRun,
    compare_evaluation_runs,
    write_evaluation_comparison,
)


def test_comparison_rejects_excessive_compression_score_drop() -> None:
    baseline = _run("uncompressed", 0.9)
    compressed = _run("compressed", 0.7)

    comparison = compare_evaluation_runs(baseline, compressed, max_score_drop=0.1)

    assert comparison.score_drop == 0.2
    assert not comparison.passed


def test_write_comparison_records_score_gate(tmp_path) -> None:
    comparison = compare_evaluation_runs(
        _run("uncompressed", 0.9), _run("compressed", 0.85), max_score_drop=0.1
    )

    path = write_evaluation_comparison(comparison, tmp_path / "comparison.yaml")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["score_drop"] == 0.05
    assert data["passed"]


def _run(name: str, score: float) -> EvaluationRun:
    return EvaluationRun(
        prompt_name="Coder",
        prompt_version="1.0.0",
        prompt_sha256=name * 8,
        suite_sha256="suite",
        model="model",
        results=(),
        mean_score=score,
        provenance={},
    )
