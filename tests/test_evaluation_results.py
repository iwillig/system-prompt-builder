from spb.evaluation import EvaluationRun, write_evaluation_run


def test_write_evaluation_run_writes_yaml(tmp_path):
    run = EvaluationRun(
        prompt_name="Coder",
        prompt_version="1.0.0",
        prompt_sha256="a" * 64,
        suite_sha256="b" * 64,
        model="test-model",
        results=(),
        mean_score=0.8,
        provenance={},
    )

    path = write_evaluation_run(run, tmp_path / "result.yaml")

    assert path == tmp_path / "result.yaml"
    assert "mean_score: 0.8" in path.read_text(encoding="utf-8")
