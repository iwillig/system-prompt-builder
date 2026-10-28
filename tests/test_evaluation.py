from pathlib import Path

import pytest
import yaml


def test_configured_prompts_have_valid_evaluation_suites() -> None:
    from spb.evaluation import load_evaluation_suite
    from spb.rendering import render_prompt

    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / ".spb/config.yaml").read_text(encoding="utf-8"))
    assert config["renders"]
    for target in config["renders"]:
        prompt = Path(target["prompt"])
        suite = load_evaluation_suite(root / ".spb" / "evals" / f"{prompt.stem}.yaml")
        rendered = render_prompt(root, root / prompt, harness=target["harness"])
        assert rendered.content
        assert suite.cases


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
    evaluation_steps:
      - Check whether a concrete bug is named.
      - Check whether its impact is explained.
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
    assert suite.metrics[1].evaluation_steps == (
        "Check whether a concrete bug is named.",
        "Check whether its impact is explained.",
    )
    assert suite.cases[0].expected_output == "A concrete bug report."
    assert suite.cases[0].mock_tools == {}
    assert suite.cases[0].expected_tool_calls is None


def test_load_evaluation_suite_reads_mock_tool_expectations(tmp_path: Path) -> None:
    from spb.evaluation import load_evaluation_suite

    suite_path = tmp_path / "tools.yaml"
    suite_path.write_text(
        """\
model: local
judge_model: local-judge
metrics:
  - type: answer_relevancy
tests:
  - name: read a file
    input: Read src/example.py and summarize it.
    mock_tools:
      read: "def answer(): return 42"
    expected_tool_calls:
      - name: read
        arguments: {path: src/example.py}
""",
        encoding="utf-8",
    )

    suite = load_evaluation_suite(suite_path)

    assert suite.cases[0].mock_tools == {"read": "def answer(): return 42"}
    assert suite.cases[0].expected_tool_calls == (
        {"name": "read", "arguments": {"path": "src/example.py"}},
    )


def test_tool_scenarios_require_configured_schema(tmp_path: Path) -> None:
    from spb.evaluation import (
        EvaluationCase,
        EvaluationSuite,
        MetricSpec,
        validate_tool_scenarios,
    )
    from spb.rendering import RenderedPrompt

    suite = EvaluationSuite(
        model="local",
        judge_model=None,
        metrics=(MetricSpec(type="answer_relevancy", threshold=0.5),),
        cases=(
            EvaluationCase(
                name="read file",
                group="tools",
                input="Read src/example.py.",
                expected_output=None,
                mock_tools={"read": "file text"},
            ),
        ),
    )
    prompt = RenderedPrompt(
        name="Assistant",
        version="1.0.0",
        content="",
        variables={},
        skills=(),
        tool_metadata=(
            {
                "name": "read",
                "summary": "Read a file.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        ),
    )

    validate_tool_scenarios(prompt, suite)
    prompt_without_schema = RenderedPrompt(
        name=prompt.name,
        version=prompt.version,
        content=prompt.content,
        variables={},
        skills=(),
        tool_metadata=({"name": "read", "summary": "Read a file."},),
    )
    with pytest.raises(ValueError, match="parameters JSON Schema"):
        validate_tool_scenarios(prompt_without_schema, suite)


def test_configured_pi_agent_tools_have_unique_names_and_schemas() -> None:
    import yaml

    config = yaml.safe_load(Path(".spb/config.yaml").read_text(encoding="utf-8"))
    tools = config["tool_provider_metadata"]["pi_agent"]["tools"]
    names = [tool["name"] for tool in tools]

    assert len(names) == len(set(names))
    assert tools
    for tool in tools:
        schema = tool["parameters"]
        assert schema["type"] == "object"
        assert isinstance(schema["properties"], dict)
        assert set(schema.get("required", [])) <= set(schema["properties"])
        assert schema["additionalProperties"] is False


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
    evaluation_steps:
      - Check whether a concrete bug is named.
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


def test_suite_requires_judge_for_answer_relevancy(tmp_path: Path) -> None:
    from spb.evaluation import load_evaluation_suite

    suite_path = tmp_path / "relevancy.yaml"
    suite_path.write_text(
        """\
model: generator
metrics:
  - type: answer_relevancy
tests:
  - name: example
    input: Answer the question.
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="require judge_model"):
        load_evaluation_suite(suite_path)


@pytest.mark.parametrize("steps", [None, [], [""], [2], "one step"])
def test_g_eval_requires_valid_explicit_steps(tmp_path: Path, steps: object) -> None:
    import yaml

    from spb.evaluation import load_evaluation_suite

    metric = {"type": "g_eval", "name": "quality", "criteria": "Check quality."}
    if steps is not None:
        metric["evaluation_steps"] = steps
    suite_path = tmp_path / "steps.yaml"
    suite_path.write_text(
        yaml.safe_dump(
            {
                "model": "generator",
                "judge_model": "judge",
                "metrics": [metric],
                "tests": [
                    {"name": "example", "input": "Answer.", "expected_output": "Yes."}
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="evaluation_steps"):
        load_evaluation_suite(suite_path)


def test_metric_builders_use_the_configured_judge_and_fixed_steps() -> None:
    from spb.evaluation import MetricSpec, _build_metric

    judge = object()
    calls = []

    def capture(**kwargs):
        calls.append(kwargs)
        return kwargs

    class Params:
        INPUT = "input"
        ACTUAL_OUTPUT = "output"
        EXPECTED_OUTPUT = "expected"

    _build_metric(MetricSpec("answer_relevancy", 0.7), capture, capture, Params, judge)
    steps = ("Check the required answer.",)
    spec = MetricSpec("g_eval", 0.7, "quality", "Check quality.", steps)
    _build_metric(spec, capture, capture, Params, judge)
    _build_metric(spec, capture, capture, Params, judge)

    assert calls[0] == {"threshold": 0.7, "model": judge}
    assert calls[1]["model"] is judge
    assert calls[1]["evaluation_steps"] == list(steps)
    assert calls[2]["evaluation_steps"] == list(steps)
    assert calls[1]["evaluation_steps"] is not calls[2]["evaluation_steps"]


def test_run_evaluation_reports_case_stages_without_endpoint_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    llm = pytest.importorskip("llm")
    pytest.importorskip("deepeval")
    from spb.evaluation import (
        EvaluationCase,
        EvaluationSuite,
        MetricSpec,
        run_evaluation,
    )
    from spb.rendering import RenderedPrompt

    class FakeMetric:
        score = 0.9
        reason = "meets the reference"

        def is_successful(self) -> bool:
            return True

    monkeypatch.setattr(
        llm,
        "get_model",
        lambda name: type(
            "FakeModel",
            (),
            {"prompt": lambda self, *a, **kw: self, "text": lambda self: "ok"},
        )(),
    )
    monkeypatch.setattr("spb.evaluation._llm_judge", lambda *args: object())
    monkeypatch.setattr(
        "spb.evaluation._build_metric", lambda *args, **kwargs: FakeMetric()
    )
    monkeypatch.setattr(
        "spb.evaluation._measure_metric_with_retry", lambda *a, **kw: None
    )
    messages: list[str] = []
    run_evaluation(
        RenderedPrompt("Example", "1.0.0", "system", {}, ()),
        EvaluationSuite(
            "generator",
            "judge",
            (MetricSpec("answer_relevancy", 0.7),),
            (EvaluationCase("sample", "default", "question", None),),
        ),
        suite_sha256="suite",
        harness="pi_agent",
        on_progress=messages.append,
    )
    assert messages == [
        "case 1/1 'sample': generating answer",
        "case 1/1 'sample': judging 'answer_relevancy'",
        "case 1/1 'sample': complete",
    ]


_JSON_ERROR = (
    "Evaluation LLM outputted an invalid JSON. Please use a better evaluation model."
)


class _FlakyMetric:
    """Fake metric whose measure() raises ValueError a fixed number of times."""

    def __init__(self, fail_times: int, message: str) -> None:
        self._fail_times = fail_times
        self._message = message
        self.attempts = 0

    def measure(self, test_case: object) -> None:
        self.attempts += 1
        if self.attempts <= self._fail_times:
            raise ValueError(self._message)


def test_measure_retries_on_judge_json_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from spb.evaluation import _measure_metric_with_retry

    monkeypatch.setattr("spb.evaluation._JUDGE_RETRY_DELAY_SECONDS", 0.0)
    metric = _FlakyMetric(2, _JSON_ERROR)

    retries = []
    _measure_metric_with_retry(
        metric,
        object(),
        on_retry=lambda attempt, total: retries.append((attempt, total)),
    )

    assert metric.attempts == 3
    assert retries == [(2, 3), (3, 3)]


def test_measure_gives_up_after_max_attempts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from spb.evaluation import _JUDGE_MAX_ATTEMPTS, _measure_metric_with_retry

    monkeypatch.setattr("spb.evaluation._JUDGE_RETRY_DELAY_SECONDS", 0.0)
    metric = _FlakyMetric(999, _JSON_ERROR)

    with pytest.raises(ValueError, match="invalid JSON"):
        _measure_metric_with_retry(metric, object())

    assert metric.attempts == _JUDGE_MAX_ATTEMPTS


def test_measure_fails_fast_on_non_json_error() -> None:
    from spb.evaluation import _measure_metric_with_retry

    metric = _FlakyMetric(999, "some unrelated configuration problem")

    with pytest.raises(ValueError, match="unrelated configuration"):
        _measure_metric_with_retry(metric, object())

    assert metric.attempts == 1
