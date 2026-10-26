from pathlib import Path


def test_load_evaluation_suite_reads_model_metrics_and_cases(tmp_path: Path) -> None:
    from spb.evaluation import load_evaluation_suite

    suite_path = tmp_path / "coder.yaml"
    suite_path.write_text(
        """\
model: gpt-4o-mini
judge_model: local-judge
metrics:
  - type: answer_relevancy
    threshold: 0.7
  - type: g_eval
    name: Coding quality
    criteria: Identifies concrete bugs and explains their impact.
tests:
  - name: reviews a function
    input: Review this function for bugs.
    expected_output: A concrete bug report.
""",
        encoding="utf-8",
    )

    suite = load_evaluation_suite(suite_path)

    assert suite.model == "gpt-4o-mini"
    assert suite.judge_model == "local-judge"
    assert suite.metrics[1].type == "g_eval"
    assert suite.cases[0].expected_output == "A concrete bug report."


def test_g_eval_suite_requires_expected_output(tmp_path: Path) -> None:
    from spb.evaluation import load_evaluation_suite

    suite_path = tmp_path / "coder.yaml"
    suite_path.write_text(
        """\
model: gpt-4o-mini
judge_model: local-judge
metrics:
  - type: g_eval
    name: Coding quality
    criteria: Identifies concrete bugs.
tests:
  - name: reviews a function
    input: Review this function for bugs.
""",
        encoding="utf-8",
    )

    try:
        load_evaluation_suite(suite_path)
    except ValueError as error:
        assert "expected_output" in str(error)
    else:
        raise AssertionError("Expected suite validation to fail")
