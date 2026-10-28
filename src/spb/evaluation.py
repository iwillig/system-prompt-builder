"""DeepEval-backed evaluation of compiled system prompts."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from spb.rendering import RenderedPrompt


@dataclass(frozen=True)
class MetricSpec:
    type: str
    threshold: float | None
    name: str | None = None
    criteria: str | None = None


@dataclass(frozen=True)
class EvaluationCase:
    name: str
    group: str
    input: str
    expected_output: str | None
    mock_tools: dict[str, str] = field(default_factory=dict)
    expected_tool_calls: tuple[dict[str, Any], ...] | None = None


@dataclass(frozen=True)
class EvaluationSuite:
    model: str
    judge_model: str | None
    metrics: tuple[MetricSpec, ...]
    cases: tuple[EvaluationCase, ...]


@dataclass(frozen=True)
class EvaluationComparison:
    """Score comparison between rendered prompt variants."""

    baseline: EvaluationRun
    candidate: EvaluationRun
    score_drop: float
    max_score_drop: float
    group_score_drops: dict[str, float]

    @property
    def passed(self) -> bool:
        return self.score_drop <= self.max_score_drop


@dataclass(frozen=True)
class EvaluationRun:
    """Serializable results and provenance for one evaluation run."""

    prompt_name: str
    prompt_version: str
    prompt_sha256: str
    suite_sha256: str
    model: str
    results: tuple[dict[str, Any], ...]
    mean_score: float
    provenance: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "prompt": {
                "name": self.prompt_name,
                "version": self.prompt_version,
                "rendered_sha256": self.prompt_sha256,
            },
            "suite": {"sha256": self.suite_sha256, "model": self.model},
            "mean_score": self.mean_score,
            "provenance": self.provenance,
            "results": list(self.results),
        }


def compare_evaluation_runs(
    baseline: EvaluationRun, candidate: EvaluationRun, *, max_score_drop: float
) -> EvaluationComparison:
    """Compare candidate quality with the uncompressed baseline."""
    if not 0 <= max_score_drop <= 1:
        raise ValueError("Maximum score drop must be between 0 and 1")
    return EvaluationComparison(
        baseline=baseline,
        candidate=candidate,
        score_drop=round(baseline.mean_score - candidate.mean_score, 10),
        max_score_drop=max_score_drop,
        group_score_drops={
            group: round(baseline_score - candidate_scores[group], 10)
            for group, baseline_score in group_mean_scores(baseline).items()
            if (candidate_scores := group_mean_scores(candidate)).get(group) is not None
        },
    )


def write_evaluation_comparison(
    comparison: EvaluationComparison, output_path: Path
) -> Path:
    """Write a compressed-prompt comparison artifact."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(
            {
                "baseline": comparison.baseline.as_dict(),
                "candidate": comparison.candidate.as_dict(),
                "score_drop": comparison.score_drop,
                "max_score_drop": comparison.max_score_drop,
                "group_score_drops": comparison.group_score_drops,
                "passed": comparison.passed,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return output_path


def write_evaluation_run(run: EvaluationRun, output_path: Path) -> Path:
    """Write an evaluation result to an explicit artifact path."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        yaml.safe_dump(run.as_dict(), sort_keys=False), encoding="utf-8"
    )
    return output_path


def load_evaluation_suite(path: Path) -> EvaluationSuite:
    """Load and validate an evaluation suite from YAML."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Evaluation suite must be a YAML mapping")
    model = _required_string(data, "model")
    metrics = tuple(_metric(metric) for metric in _required_list(data, "metrics"))
    cases = tuple(_case(case) for case in _required_list(data, "tests"))
    if not metrics or not cases:
        raise ValueError("Evaluation suite must define metrics and tests")
    has_g_eval = any(metric.type == "g_eval" for metric in metrics)
    if has_g_eval and any(case.expected_output is None for case in cases):
        raise ValueError("g_eval suites require expected_output for every test")
    judge_model = data.get("judge_model")
    if has_g_eval and (not isinstance(judge_model, str) or not judge_model):
        raise ValueError("g_eval suites require judge_model")
    return EvaluationSuite(
        model=model,
        judge_model=judge_model if isinstance(judge_model, str) else None,
        metrics=metrics,
        cases=cases,
    )


_JUDGE_MAX_ATTEMPTS = 3
_JUDGE_RETRY_DELAY_SECONDS = 1.0


def _is_judge_json_error(error: ValueError) -> bool:
    """Return True for the reference-free judge's malformed-JSON failure."""
    return "invalid json" in str(error).lower()


def _measure_metric_with_retry(metric: Any, test_case: Any) -> None:
    """Run metric.measure, retrying transient judge JSON-parse failures.

    The reference-free judge (G-Eval) occasionally emits malformed JSON; DeepEval
    surfaces that as a ValueError. Re-run measure up to _JUDGE_MAX_ATTEMPTS
    times, re-raising on the final attempt or on any non-JSON ValueError.
    """
    for attempt in range(_JUDGE_MAX_ATTEMPTS):
        try:
            metric.measure(test_case)
            return
        except ValueError as error:
            if not _is_judge_json_error(error) or attempt + 1 >= _JUDGE_MAX_ATTEMPTS:
                raise
            time.sleep(_JUDGE_RETRY_DELAY_SECONDS)


def run_evaluation(
    prompt: RenderedPrompt,
    suite: EvaluationSuite,
    *,
    suite_sha256: str,
    harness: str,
) -> EvaluationRun:
    """Generate model responses, including mock-tool chains, and evaluate them."""
    try:
        import llm
        from deepeval.metrics import (
            AnswerRelevancyMetric,
            GEval,
        )
        from deepeval.models.base_model import (
            DeepEvalBaseLLM,
        )
        from deepeval.test_case import (
            LLMTestCase,
            SingleTurnParams,
        )
        from deepeval.test_case import (
            ToolCall as DeepEvalToolCall,
        )
    except ImportError as error:
        raise ValueError(
            "Evaluation dependencies are not installed; install the eval "
            "optional dependency"
        ) from error

    model = llm.get_model(suite.model)
    judge = _llm_judge(llm, DeepEvalBaseLLM, suite.judge_model)
    results: list[dict[str, Any]] = []
    scores: list[float] = []
    validate_tool_scenarios(prompt, suite)
    for case in suite.cases:
        tool_calls: list[dict[str, Any]] = []
        if case.mock_tools:
            tools = _mock_tools(prompt, case, llm)

            def record_tool_call(
                _tool: Any, call: Any, recorded_calls: list[dict[str, Any]] = tool_calls
            ) -> None:
                recorded_calls.append({"name": call.name, "arguments": call.arguments})

            output = model.chain(
                case.input,
                system=prompt.content,
                tools=tools,
                before_call=record_tool_call,
            ).text()
        else:
            output = model.prompt(case.input, system=prompt.content).text()
        tool_calls_passed = (
            None
            if case.expected_tool_calls is None
            else tool_calls == list(case.expected_tool_calls)
        )
        test_case = LLMTestCase(
            input=case.input,
            actual_output=output,
            expected_output=case.expected_output,
            tools_called=[
                DeepEvalToolCall(name=call["name"], input_parameters=call["arguments"])
                for call in tool_calls
            ],
            expected_tools=(
                [
                    DeepEvalToolCall(
                        name=call["name"], input_parameters=call["arguments"]
                    )
                    for call in case.expected_tool_calls
                ]
                if case.expected_tool_calls is not None
                else None
            ),
        )
        metric_results: list[dict[str, Any]] = []
        for spec in suite.metrics:
            metric = _build_metric(
                spec,
                AnswerRelevancyMetric,
                GEval,
                SingleTurnParams,
                judge,
                include_tool_trace=case.expected_tool_calls is not None,
            )
            _measure_metric_with_retry(metric, test_case)
            score = float(metric.score)
            scores.append(score)
            metric_results.append(
                {
                    "name": spec.name or spec.type,
                    "score": score,
                    "threshold": spec.threshold,
                    "passed": bool(metric.is_successful()),
                    "reason": metric.reason,
                }
            )
        results.append(
            {
                "name": case.name,
                "group": case.group,
                "input": case.input,
                "output": output,
                "tool_calls": tool_calls,
                "expected_tool_calls": (
                    list(case.expected_tool_calls)
                    if case.expected_tool_calls is not None
                    else None
                ),
                "tool_calls_passed": tool_calls_passed,
                "metrics": metric_results,
            }
        )
    return EvaluationRun(
        prompt_name=prompt.name,
        prompt_version=prompt.version,
        prompt_sha256=hashlib.sha256(prompt.content.encode("utf-8")).hexdigest(),
        suite_sha256=suite_sha256,
        model=suite.model,
        results=tuple(results),
        mean_score=sum(scores) / len(scores),
        provenance={
            "harness": harness,
            "judge_model": suite.judge_model,
            "variables": _visible_variables(prompt.variables),
            "skills": [
                {
                    "reference": skill.reference,
                    "sha256": skill.sha256,
                    "gitrepo": skill.gitrepo,
                    "revision": skill.revision,
                }
                for skill in prompt.skills
            ],
            "compression": None,
        },
    )


def group_mean_scores(run: EvaluationRun) -> dict[str, float]:
    """Return the mean metric score for every named benchmark group."""
    grouped_scores: dict[str, list[float]] = {}
    for case in run.results:
        group = str(case.get("group", "default"))
        for metric in case.get("metrics", []):
            grouped_scores.setdefault(group, []).append(float(metric["score"]))
    return {
        group: sum(scores) / len(scores)
        for group, scores in sorted(grouped_scores.items())
        if scores
    }


def validate_tool_scenarios(prompt: RenderedPrompt, suite: EvaluationSuite) -> None:
    """Check that case mocks refer to configured, schema-backed tools."""
    configured = {tool.get("name"): tool for tool in prompt.tool_metadata}
    for case in suite.cases:
        for name in case.mock_tools:
            tool = configured.get(name)
            if tool is None:
                raise ValueError(
                    f"Evaluation case {case.name!r} mocks unknown configured tool "
                    f"{name!r}"
                )
            if not isinstance(tool.get("parameters"), dict):
                raise ValueError(
                    f"Configured tool {name!r} needs a parameters JSON Schema "
                    "to be used in a mock evaluation"
                )
        if case.expected_tool_calls is not None:
            if not case.mock_tools and case.expected_tool_calls:
                raise ValueError(
                    f"Evaluation case {case.name!r} expects tool calls but "
                    "defines no mock_tools"
                )
            for expected in case.expected_tool_calls:
                if expected["name"] not in case.mock_tools:
                    raise ValueError(
                        f"Evaluation case {case.name!r} expects unmocked tool "
                        f"{expected['name']!r}"
                    )


def _mock_tools(
    prompt: RenderedPrompt, case: EvaluationCase, llm_module: Any
) -> list[Any]:
    configured = {tool["name"]: tool for tool in prompt.tool_metadata}
    tools = []
    for name, result in case.mock_tools.items():
        metadata = configured[name]

        def mock_implementation(result_text: str) -> Any:
            def implementation(**_arguments: Any) -> str:
                return result_text

            return implementation

        tools.append(
            llm_module.Tool(
                name=name,
                description=metadata.get("summary"),
                input_schema=metadata["parameters"],
                implementation=mock_implementation(result),
            )
        )
    return tools


def _visible_variables(variables: dict[str, Any]) -> dict[str, Any]:
    secret_words = ("password", "secret", "token", "key")
    return {
        name: value
        for name, value in variables.items()
        if not any(word in name.lower() for word in secret_words)
    }


def _llm_judge(llm_module: Any, base_class: Any, model_id: str | None) -> Any:
    if model_id is None:
        return None

    judge_model = model_id

    class LlmJudge(base_class):  # type: ignore[misc]
        def load_model(self) -> Any:
            return llm_module.get_model(model_id)

        def generate(self, prompt: str) -> str:
            return str(self.load_model().prompt(prompt).text())

        async def a_generate(self, prompt: str) -> str:
            return self.generate(prompt)

        def get_model_name(self) -> str:
            return judge_model

    return LlmJudge()


def _build_metric(
    spec: MetricSpec,
    answer_relevancy: Any,
    g_eval: Any,
    params: Any,
    judge: Any,
    *,
    include_tool_trace: bool = False,
) -> Any:
    if spec.type == "answer_relevancy":
        return answer_relevancy(threshold=spec.threshold)
    evaluation_params = [params.INPUT, params.ACTUAL_OUTPUT, params.EXPECTED_OUTPUT]
    if include_tool_trace:
        evaluation_params.extend([params.TOOLS_CALLED, params.EXPECTED_TOOLS])
    return g_eval(
        name=spec.name or "G-Eval",
        criteria=spec.criteria or "",
        threshold=spec.threshold,
        model=judge,
        evaluation_params=evaluation_params,
    )


def _metric(value: Any) -> MetricSpec:
    if not isinstance(value, dict):
        raise ValueError("Each metric must be a mapping")
    metric_type = _required_string(value, "type")
    threshold = value.get("threshold", 0.5)
    if not isinstance(threshold, (int, float)):
        raise ValueError("Metric threshold must be a number")
    if metric_type == "answer_relevancy":
        return MetricSpec(type=metric_type, threshold=float(threshold))
    if metric_type == "g_eval":
        return MetricSpec(
            type=metric_type,
            threshold=float(threshold),
            name=_required_string(value, "name"),
            criteria=_required_string(value, "criteria"),
        )
    raise ValueError(f"Unsupported DeepEval metric: {metric_type}")


def _case(value: Any) -> EvaluationCase:
    if not isinstance(value, dict):
        raise ValueError("Each test must be a mapping")
    expected_output = value.get("expected_output")
    if expected_output is not None and not isinstance(expected_output, str):
        raise ValueError("Test expected_output must be a string")
    mock_tools = value.get("mock_tools", {})
    if not isinstance(mock_tools, dict) or not all(
        isinstance(name, str) and name and isinstance(result, str)
        for name, result in mock_tools.items()
    ):
        raise ValueError("Test mock_tools must map tool names to string results")
    expected_tool_calls_value = value.get("expected_tool_calls")
    expected_tool_calls: tuple[dict[str, Any], ...] | None = None
    if expected_tool_calls_value is not None:
        if not isinstance(expected_tool_calls_value, list):
            raise ValueError("Test expected_tool_calls must be a list")
        expected_tool_calls_list = []
        for call in expected_tool_calls_value:
            if (
                not isinstance(call, dict)
                or not isinstance(call.get("name"), str)
                or not call["name"]
                or not isinstance(call.get("arguments"), dict)
            ):
                raise ValueError(
                    "Each expected_tool_calls entry needs a name and arguments mapping"
                )
            expected_tool_calls_list.append(
                {"name": call["name"], "arguments": call["arguments"]}
            )
        expected_tool_calls = tuple(expected_tool_calls_list)
    group = value.get("group", "default")
    if not isinstance(group, str) or not group:
        raise ValueError("Test group must be a non-empty string")
    return EvaluationCase(
        name=_required_string(value, "name"),
        group=group,
        input=_required_string(value, "input"),
        expected_output=expected_output,
        mock_tools=mock_tools,
        expected_tool_calls=expected_tool_calls,
    )


def _required_list(data: dict[str, Any], name: str) -> list[Any]:
    value = data.get(name)
    if not isinstance(value, list):
        raise ValueError(f"Evaluation suite must define {name}")
    return value


def _required_string(data: dict[str, Any], name: str) -> str:
    value = data.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Evaluation suite must define {name}")
    return value
