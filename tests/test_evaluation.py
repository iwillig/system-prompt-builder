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
    assert suite.cases[0].mock_tools == {}
    assert suite.cases[0].expected_tool_calls is None


def test_load_evaluation_suite_reads_mock_tool_expectations(tmp_path: Path) -> None:
    from spb.evaluation import load_evaluation_suite

    suite_path = tmp_path / "tools.yaml"
    suite_path.write_text(
        """\
model: local
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
