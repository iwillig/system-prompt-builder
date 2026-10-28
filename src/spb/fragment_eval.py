"""Suite-scoped fragment ablation and compression-sweep evaluation."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from pathlib import Path
from statistics import median
from typing import Any

import yaml

from spb.compression import compress_prompt
from spb.evaluation import EvaluationRun, EvaluationSuite, run_evaluation
from spb.rendering import RenderedPrompt, compose_fragment_content


@dataclass(frozen=True)
class FragmentVariant:
    alias: str
    kind: str
    rate: float | None
    prompt: RenderedPrompt
    reduction: float

    @property
    def label(self) -> str:
        return "drop" if self.kind == "drop" else f"rate={self.rate:g}"

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.prompt.content.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FragmentPlan:
    baseline: RenderedPrompt
    variants: tuple[FragmentVariant, ...]
    repeats: int
    cases: int

    @property
    def case_generations(self) -> int:
        return (1 + len(self.variants)) * self.repeats * self.cases


@dataclass(frozen=True)
class FragmentAblationReport:
    plan: FragmentPlan
    suite_sha256: str
    model: str
    judge_model: str | None
    harness: str
    noise_floor: float
    baseline_runs: tuple[EvaluationRun, ...]
    outcomes: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "prompt": {
                "name": self.plan.baseline.name,
                "version": self.plan.baseline.version,
                "baseline_sha256": hashlib.sha256(
                    self.plan.baseline.content.encode("utf-8")
                ).hexdigest(),
            },
            "suite": {
                "sha256": self.suite_sha256,
                "model": self.model,
                "judge_model": self.judge_model,
            },
            "harness": self.harness,
            "repeats": self.plan.repeats,
            "noise_floor": self.noise_floor,
            "planned_case_generations": self.plan.case_generations,
            "baseline_runs": [run.as_dict() for run in self.baseline_runs],
            "outcomes": list(self.outcomes),
            "matrix": [
                {
                    "alias": outcome["alias"],
                    "transformation": outcome["transformation"],
                    "case": metric["case"],
                    "metric": metric["metric"],
                    "median_delta": metric["variant_median"]
                    - metric["baseline_median"],
                }
                for outcome in self.outcomes
                for metric in outcome["metrics"]
            ],
        }


def plan_fragment_evaluation(
    prompt: RenderedPrompt,
    *,
    cases: int,
    repeats: int = 3,
    mode: str = "both",
    aliases: tuple[str, ...] = (),
    rates: tuple[float, ...] = (0.5, 0.3, 0.1),
    compressor: str = "llmlingua",
    max_case_generations: int | None = None,
) -> FragmentPlan:
    """Validate and construct all variants before any model call."""
    if not prompt.fragments:
        raise ValueError("Ablation requires a fragment-based prompt")
    if repeats < 1 or cases < 1 or mode not in {"drop", "rate", "both"}:
        raise ValueError(
            "Expected repeats >= 1, cases >= 1, and mode drop, rate, or both"
        )
    if len(set(aliases)) != len(aliases) or len(set(rates)) != len(rates):
        raise ValueError("Fragment aliases and compression rates must be unique")
    selected = tuple(prompt.rendered_fragments)
    if any(alias not in selected for alias in aliases):
        raise ValueError("Requested fragment alias is not selected by this prompt")
    if any(not 0 < rate <= 1 for rate in rates):
        raise ValueError("Compression rates must be between 0 and 1")
    if mode in {"rate", "both"} and not rates:
        raise ValueError("Rate sweep requires at least one rate")
    drop_aliases = (aliases or selected) if mode in {"drop", "both"} else ()
    rate_aliases = (
        (aliases or prompt.compressible_fragments) if mode in {"rate", "both"} else ()
    )
    if any(alias not in prompt.compressible_fragments for alias in rate_aliases):
        raise ValueError("Rate sweep requires compressible_fragments aliases")
    specs = [(alias, "drop", None) for alias in drop_aliases] + [
        (alias, "rate", rate) for alias in rate_aliases for rate in rates
    ]
    if not specs:
        raise ValueError("No fragment variants were selected")
    count = (1 + len(specs)) * repeats * cases
    if max_case_generations is not None and count > max_case_generations:
        raise ValueError(
            f"Planned {count} case generations exceeds cap {max_case_generations}"
        )
    variants = []
    for alias, kind, rate in specs:
        values = dict(prompt.rendered_fragments)
        if kind == "drop":
            values[alias] = ""
        else:
            assert rate is not None
            values[alias] = compress_prompt(
                values[alias], compressor, rate=rate
            ).content
            if not values[alias].strip():
                raise ValueError(f"Compressor returned empty fragment: {alias}")
        content = compose_fragment_content(prompt, values)
        if not content.strip():
            raise ValueError(f"Empty composed variant: {alias}")
        variants.append(
            FragmentVariant(
                alias,
                kind,
                rate,
                replace(prompt, content=content, rendered_fragments=values),
                1 - len(content) / len(prompt.content),
            )
        )
    return FragmentPlan(prompt, tuple(variants), repeats, cases)


def _case_index(run: EvaluationRun) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for case in run.results:
        for metric in case["metrics"]:
            key = (case["name"], metric["name"])
            if key in index:
                raise ValueError(f"Duplicate case/metric identity: {key}")
            index[key] = metric
    return index


def _trace_index(run: EvaluationRun) -> dict[str, dict[str, Any]]:
    index = {}
    for case in run.results:
        if case["name"] in index:
            raise ValueError(f"Duplicate case identity: {case['name']}")
        index[case["name"]] = case
    return index


def aggregate_variant(
    baseline: tuple[EvaluationRun, ...],
    variant: tuple[EvaluationRun, ...],
    *,
    noise_floor: float,
) -> dict[str, Any]:
    """Classify matching per-case metrics and traces; retain raw observations."""
    if not baseline or len(baseline) != len(variant):
        raise ValueError("Baseline and variant must have the same nonzero repeat count")
    all_runs = baseline + variant
    if any(
        run.suite_sha256 != baseline[0].suite_sha256 or run.model != baseline[0].model
        for run in all_runs
    ):
        raise ValueError("Runs have mismatched suite or model")
    b_index = [_case_index(run) for run in baseline]
    v_index = [_case_index(run) for run in variant]
    b_traces = [_trace_index(run) for run in baseline]
    v_traces = [_trace_index(run) for run in variant]
    keys = set(b_index[0])
    cases = set(b_traces[0])
    if any(set(index) != keys for index in b_index + v_index) or any(
        set(index) != cases for index in b_traces + v_traces
    ):
        raise ValueError("Runs contain mismatched case/metric identities")
    reasons: list[str] = []
    regressions: list[str] = []
    metrics = []
    n = len(baseline)
    for case, name in sorted(keys):
        entries_b = [index[(case, name)] for index in b_index]
        entries_v = [index[(case, name)] for index in v_index]
        thresholds = {entry["threshold"] for entry in entries_b + entries_v}
        if len(thresholds) != 1:
            raise ValueError(f"Mismatched threshold for {case}/{name}")
        bp = sum(bool(e["passed"]) for e in entries_b)
        vp = sum(bool(e["passed"]) for e in entries_v)
        bs = [float(e["score"]) for e in entries_b]
        vs = [float(e["score"]) for e in entries_v]
        key = f"{case}/{name}"
        if bp == n and n - vp > n / 2:
            regressions.append(f"metric majority failure: {key}")
        elif bp == 0:
            reasons.append(f"baseline metric never passed: {key}")
        elif bp != n:
            reasons.append(f"baseline metric mixed: {key}")
        elif vp != n:
            reasons.append(f"variant metric mixed: {key}")
        elif median(bs) - median(vs) > noise_floor:
            reasons.append(f"material score decrease: {key}")
        metrics.append(
            {
                "case": case,
                "metric": name,
                "threshold": entries_b[0]["threshold"],
                "baseline_scores": bs,
                "variant_scores": vs,
                "baseline_passes": bp,
                "variant_passes": vp,
                "baseline_median": median(bs),
                "variant_median": median(vs),
                "baseline_min": min(bs),
                "variant_min": min(vs),
                "baseline_max": max(bs),
                "variant_max": max(vs),
            }
        )
    traces = []
    for case in sorted(cases):
        baseline_cases = [index[case] for index in b_traces]
        variant_cases = [index[case] for index in v_traces]
        expectations = [
            entry["expected_tool_calls"] for entry in baseline_cases + variant_cases
        ]
        if any(expected != expectations[0] for expected in expectations):
            raise ValueError(f"Mismatched tool expectation: {case}")
        if expectations[0] is None:
            continue
        bp = sum(entry["tool_calls_passed"] is True for entry in baseline_cases)
        vp = sum(entry["tool_calls_passed"] is True for entry in variant_cases)
        if bp == n and n - vp > n / 2:
            regressions.append(f"tool trace majority failure: {case}")
        elif bp != n:
            reasons.append(f"baseline tool trace unstable: {case}")
        elif vp != n:
            reasons.append(f"variant tool trace mixed: {case}")
        traces.append(
            {
                "case": case,
                "expected": expectations[0],
                "baseline_passes": bp,
                "variant_passes": vp,
                "baseline_calls": [entry["tool_calls"] for entry in baseline_cases],
                "variant_calls": [entry["tool_calls"] for entry in variant_cases],
            }
        )
    if regressions:
        verdict = "REGRESSION"
        reasons = regressions + reasons
    elif n < 3 or reasons or not keys:
        verdict = "INDETERMINATE"
        if n < 3:
            reasons.append("fewer than three repeats")
        if not keys:
            reasons.append("no scored metrics")
    else:
        verdict = "NO_REGRESSION_DETECTED"
    return {
        "verdict": verdict,
        "reasons": reasons,
        "exploratory": n < 3,
        "metrics": metrics,
        "traces": traces,
    }


def evaluate_fragment_plan(
    plan: FragmentPlan,
    suite: EvaluationSuite,
    *,
    suite_sha256: str,
    harness: str,
    noise_floor: float = 0.1,
) -> FragmentAblationReport:
    if not 0 <= noise_floor <= 1:
        raise ValueError("Noise floor must be between 0 and 1")
    if plan.cases != len(suite.cases):
        raise ValueError("Plan case count does not match suite")

    def runs(prompt: RenderedPrompt) -> tuple[EvaluationRun, ...]:
        expected_hash = hashlib.sha256(prompt.content.encode("utf-8")).hexdigest()
        results = tuple(
            run_evaluation(prompt, suite, suite_sha256=suite_sha256, harness=harness)
            for _ in range(plan.repeats)
        )
        if any(
            run.prompt_sha256 != expected_hash
            or run.suite_sha256 != suite_sha256
            or run.model != suite.model
            for run in results
        ):
            raise ValueError(
                "Evaluation results do not match the planned prompt or suite"
            )
        return results

    baseline = runs(plan.baseline)
    outcomes = []
    for variant in plan.variants:
        current = runs(variant.prompt)
        outcome = aggregate_variant(baseline, current, noise_floor=noise_floor)
        outcome.update(
            {
                "alias": variant.alias,
                "transformation": variant.label,
                "prompt_sha256": variant.sha256,
                "reduction_chars": variant.reduction,
                "runs": [run.as_dict() for run in current],
            }
        )
        outcomes.append(outcome)
    return FragmentAblationReport(
        plan,
        suite_sha256,
        suite.model,
        suite.judge_model,
        harness,
        noise_floor,
        baseline,
        tuple(outcomes),
    )


def write_fragment_report(report: FragmentAblationReport, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(report.as_dict(), sort_keys=False), encoding="utf-8")
    return path
