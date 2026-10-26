"""DeepEval-backed evaluation of compiled system prompts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
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
    input: str
    expected_output: str | None


@dataclass(frozen=True)
class EvaluationSuite:
    model: str
    metrics: tuple[MetricSpec, ...]
    cases: tuple[EvaluationCase, ...]


@dataclass(frozen=True)
class EvaluationComparison:
    """Score comparison between rendered prompt variants."""

    baseline: EvaluationRun
    candidate: EvaluationRun
    score_drop: float
    max_score_drop: float

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
    if any(metric.type == "g_eval" for metric in metrics) and any(
        case.expected_output is None for case in cases
    ):
        raise ValueError("g_eval suites require expected_output for every test")
    return EvaluationSuite(model=model, metrics=metrics, cases=cases)


def run_evaluation(
    prompt: RenderedPrompt,
    suite: EvaluationSuite,
    *,
    suite_sha256: str,
    harness: str,
) -> EvaluationRun:
    """Generate direct model responses and evaluate them with DeepEval."""
    try:
        import llm  # type: ignore[import-not-found]
        from deepeval.metrics import (  # type: ignore[import-not-found]
            AnswerRelevancyMetric,
            GEval,
        )
        from deepeval.test_case import (  # type: ignore[import-not-found]
            LLMTestCase,
            SingleTurnParams,
        )
    except ImportError as error:
        raise ValueError(
            "Evaluation dependencies are not installed; install the eval "
            "optional dependency"
        ) from error

    model = llm.get_model(suite.model)
    results: list[dict[str, Any]] = []
    scores: list[float] = []
    for case in suite.cases:
        output = model.prompt(case.input, system=prompt.content).text()
        test_case = LLMTestCase(
            input=case.input, actual_output=output, expected_output=case.expected_output
        )
        metric_results: list[dict[str, Any]] = []
        for spec in suite.metrics:
            metric = _build_metric(spec, AnswerRelevancyMetric, GEval, SingleTurnParams)
            metric.measure(test_case)
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
                "input": case.input,
                "output": output,
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


def _visible_variables(variables: dict[str, Any]) -> dict[str, Any]:
    secret_words = ("password", "secret", "token", "key")
    return {
        name: value
        for name, value in variables.items()
        if not any(word in name.lower() for word in secret_words)
    }


def _build_metric(
    spec: MetricSpec, answer_relevancy: Any, g_eval: Any, params: Any
) -> Any:
    if spec.type == "answer_relevancy":
        return answer_relevancy(threshold=spec.threshold)
    return g_eval(
        name=spec.name or "G-Eval",
        criteria=spec.criteria or "",
        threshold=spec.threshold,
        evaluation_params=[params.INPUT, params.ACTUAL_OUTPUT, params.EXPECTED_OUTPUT],
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
    return EvaluationCase(
        name=_required_string(value, "name"),
        input=_required_string(value, "input"),
        expected_output=expected_output,
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
