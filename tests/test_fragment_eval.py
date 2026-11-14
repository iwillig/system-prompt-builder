import hashlib
from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from spb.evaluation import EvaluationRun, load_evaluation_suite
from spb.fragment_eval import (
    aggregate_variant,
    evaluate_fragment_plan,
    plan_fragment_evaluation,
    write_fragment_report,
)
from spb.rendering import render_prompt


def _run(
    score: float = 0.9,
    *,
    passed: bool = True,
    trace_passed: bool | None = None,
    second_metric: bool = False,
) -> EvaluationRun:
    metrics = [{"name": "quality", "score": score, "threshold": 0.7, "passed": passed}]
    if second_metric:
        metrics.append(
            {"name": "accuracy", "score": 0.8, "threshold": 0.7, "passed": True}
        )
    return EvaluationRun(
        "Example",
        "1.0.0",
        "hash",
        "suite",
        "model",
        (
            {
                "name": "example",
                "metrics": metrics,
                "expected_tool_calls": (
                    [{"name": "tool", "arguments": {}}]
                    if trace_passed is not None
                    else None
                ),
                "tool_calls": (
                    [{"name": "tool", "arguments": {}}] if trace_passed else []
                ),
                "tool_calls_passed": trace_passed,
            },
        ),
        score,
        {},
    )


def test_aggregate_no_regression_requires_stable_three_repeats() -> None:
    stable = (_run(),) * 3
    result = aggregate_variant(stable, stable, noise_floor=0.1)
    assert result["verdict"] == "NO_REGRESSION_DETECTED"
    assert (
        aggregate_variant(stable[:1], stable[:1], noise_floor=0.1)["verdict"]
        == "INDETERMINATE"
    )
    mixed = aggregate_variant(
        stable, (_run(passed=False), stable[0], stable[0]), noise_floor=0.1
    )
    assert mixed["verdict"] == "INDETERMINATE"
    assert mixed["reasons"] == ["variant metric mixed: example/quality"]


def test_aggregate_majority_failure_and_unstable_baseline() -> None:
    baseline = (_run(),) * 3
    failing = (_run(0.2, passed=False),) * 2 + (_run(),)
    assert (
        aggregate_variant(baseline, failing, noise_floor=0.1)["verdict"] == "REGRESSION"
    )
    unstable = (_run(passed=False),) + baseline[:2]
    unstable_result = aggregate_variant(unstable, failing, noise_floor=0.1)
    assert unstable_result["verdict"] == "INDETERMINATE"
    assert unstable_result["reasons"] == ["baseline metric mixed: example/quality"]


def test_aggregate_trace_majority_and_baseline_guard() -> None:
    baseline = (_run(trace_passed=True),) * 3
    variant = (_run(trace_passed=False),) * 2 + baseline[:1]
    report = aggregate_variant(baseline, variant, noise_floor=0.1)
    assert report["verdict"] == "REGRESSION"
    assert report["traces"][0]["variant_passes"] == 1
    unstable = baseline[:2] + (_run(trace_passed=False),)
    unstable_result = aggregate_variant(unstable, variant, noise_floor=0.1)
    assert unstable_result["verdict"] == "INDETERMINATE"
    assert unstable_result["reasons"] == ["baseline tool trace unstable: example"]


def test_aggregate_even_tie_and_threshold_mismatch() -> None:
    baseline = (_run(),) * 4
    tied = (_run(passed=False),) * 2 + baseline[:2]
    assert (
        aggregate_variant(baseline, tied, noise_floor=0.1)["verdict"] == "INDETERMINATE"
    )
    mismatched = replace(
        _run(),
        results=(
            {
                **_run().results[0],
                "metrics": [{**_run().results[0]["metrics"][0], "threshold": 0.8}],
            },
        ),
    )
    with pytest.raises(ValueError, match="threshold"):
        aggregate_variant(baseline, (mismatched,) * 4, noise_floor=0.1)


def test_aggregate_metric_identity_and_noise_guard() -> None:
    baseline = (_run(0.95),) * 3
    variant = (_run(0.8),) * 3
    result = aggregate_variant(baseline, variant, noise_floor=0.1)
    assert result["verdict"] == "INDETERMINATE"
    assert result["metrics"][0]["baseline_median"] == 0.95
    with pytest.raises(ValueError, match="identities"):
        aggregate_variant(baseline, (_run(second_metric=True),) * 3, noise_floor=0.1)
    with pytest.raises(ValueError, match="Duplicate"):
        aggregate_variant(
            baseline,
            (replace(_run(), results=_run().results * 2),) * 3,
            noise_floor=0.1,
        )


def test_plan_builds_independent_variants_and_caps_before_compression() -> None:
    prompt = render_prompt(
        Path("."), Path(".spb/prompts/python-assistant.md"), harness="pi_agent"
    )
    plan = plan_fragment_evaluation(
        prompt,
        cases=2,
        repeats=3,
        mode="both",
        aliases=("routing",),
        rates=(0.5, 0.2),
        compressor="none",
    )
    assert plan.case_generations == 24
    assert [variant.label for variant in plan.variants] == [
        "drop",
        "rate=0.5",
        "rate=0.2",
    ]
    assert prompt.rendered_fragments["routing"]
    assert plan.variants[0].prompt.rendered_fragments["routing"] == ""
    assert plan.variants[0].prompt.content != prompt.content
    assert plan.variants[1].prompt.content == prompt.content
    with pytest.raises(ValueError, match="exceeds cap"):
        plan_fragment_evaluation(
            prompt, cases=2, mode="rate", aliases=("routing",), max_case_generations=1
        )
    with pytest.raises(ValueError, match="compressible"):
        plan_fragment_evaluation(prompt, cases=2, mode="rate", aliases=("rules",))
    with pytest.raises(ValueError, match="unique"):
        plan_fragment_evaluation(
            prompt, cases=2, mode="drop", aliases=("routing", "routing")
        )


def test_plan_evaluation_reuses_baseline_and_writes_matrix(
    monkeypatch, tmp_path: Path
) -> None:
    prompt = render_prompt(
        Path("."), Path(".spb/prompts/python-assistant.md"), harness="pi_agent"
    )
    suite = load_evaluation_suite(Path(".spb/evals/python-assistant-hf.yaml"))
    plan = plan_fragment_evaluation(
        prompt,
        cases=len(suite.cases),
        mode="both",
        aliases=("routing",),
        rates=(0.5,),
        compressor="none",
    )
    calls = []

    def fake_run(prompt, suite, *, suite_sha256, harness):
        calls.append(prompt.content)
        return replace(
            _run(),
            prompt_sha256=hashlib.sha256(prompt.content.encode("utf-8")).hexdigest(),
            model=suite.model,
        )

    monkeypatch.setattr("spb.fragment_eval.run_evaluation", fake_run)
    report = evaluate_fragment_plan(
        plan, suite, suite_sha256="suite", harness="pi_agent"
    )
    assert len(calls) == 9
    assert calls[:3] == [prompt.content] * 3
    assert [outcome["verdict"] for outcome in report.outcomes] == [
        "NO_REGRESSION_DETECTED"
    ] * 2
    data = yaml.safe_load(
        write_fragment_report(report, tmp_path / "out.yaml").read_text()
    )
    assert data["planned_case_generations"] == 9 * len(suite.cases)
    assert data["matrix"][0]["case"] == "example"
    assert data["matrix"][0]["metric"] == "quality"
    assert len(data["baseline_runs"]) == 3


def test_plan_rejects_evaluation_for_wrong_prompt(monkeypatch) -> None:
    prompt = render_prompt(
        Path("."), Path(".spb/prompts/python-assistant.md"), harness="pi_agent"
    )
    suite = load_evaluation_suite(Path(".spb/evals/python-assistant-hf.yaml"))
    plan = plan_fragment_evaluation(
        prompt,
        cases=len(suite.cases),
        mode="drop",
        aliases=("routing",),
        repeats=1,
    )
    monkeypatch.setattr("spb.fragment_eval.run_evaluation", lambda *a, **kw: _run())
    with pytest.raises(ValueError, match="planned prompt"):
        evaluate_fragment_plan(plan, suite, suite_sha256="suite", harness="pi_agent")


def test_cli_dry_run_and_preflight_cap_do_not_call_model(monkeypatch) -> None:
    from spb.cli import cli

    def forbidden(*args, **kwargs):
        raise AssertionError("Model was called")

    monkeypatch.setattr("spb.fragment_eval.run_evaluation", forbidden)
    args = [
        "eval",
        "ablate",
        ".spb/prompts/python-assistant.md",
        "--suite",
        ".spb/evals/python-assistant-hf.yaml",
        "--harness",
        "pi_agent",
        "--mode",
        "drop",
        "--fragments",
        "routing",
    ]
    dry = CliRunner().invoke(cli, args + ["--dry-run"])
    assert dry.exit_code == 0, dry.output
    assert "Planned case generations: 102" in dry.output
    blocked = CliRunner().invoke(cli, args + ["--max-case-generations", "100"])
    assert blocked.exit_code != 0
    assert "exceeds cap" in blocked.output


def test_cli_writes_live_report_with_stubbed_evaluation(
    monkeypatch, tmp_path: Path
) -> None:
    from spb.cli import cli

    calls = []

    def fake_run(prompt, suite, *, suite_sha256, harness, on_progress=None):
        calls.append(prompt.content)
        if on_progress is not None:
            on_progress("case 1/1 'example': generating answer")
            on_progress("case 1/1 'example': judging 'quality'")
        return replace(
            _run(),
            prompt_sha256=hashlib.sha256(prompt.content.encode("utf-8")).hexdigest(),
            suite_sha256=suite_sha256,
            model=suite.model,
        )

    monkeypatch.setattr("spb.fragment_eval.run_evaluation", fake_run)
    output = tmp_path / "ablation.yaml"
    result = CliRunner().invoke(
        cli,
        [
            "eval",
            "ablate",
            ".spb/prompts/python-assistant.md",
            "--suite",
            ".spb/evals/python-assistant-hf.yaml",
            "--harness",
            "pi_agent",
            "--mode",
            "drop",
            "--fragments",
            "routing",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 0, result.output
    assert len(calls) == 6
    assert "NO_REGRESSION_DETECTED" in result.output
    assert "baseline, repeat 1/3: starting" in result.output
    assert (
        "baseline, repeat 1/3: case 1/1 'example': judging 'quality'" in result.output
    )
    assert "routing drop, repeat 3/3: complete" in result.output
    assert "mean score 0.900 -> 0.900" in result.output
    assert f"Report: {output}" in result.output
    artifact = yaml.safe_load(output.read_text())
    assert artifact["planned_case_generations"] == 102
    assert artifact["outcomes"][0]["transformation"] == "drop"
    assert artifact["status"] == "complete"
    assert not Path(str(output) + ".partial").exists()


def test_cli_explains_exploratory_verdict_and_disagreeing_pass_flags(
    monkeypatch, tmp_path: Path
) -> None:
    from spb.cli import cli

    def fake_run(prompt, suite, *, suite_sha256, harness, on_progress):
        on_progress("case 1/1 'example': judging 'quality'")
        return replace(
            _run(passed=prompt.content == baseline_prompt.content),
            prompt_sha256=hashlib.sha256(prompt.content.encode("utf-8")).hexdigest(),
            suite_sha256=suite_sha256,
            model=suite.model,
        )

    baseline_prompt = render_prompt(
        Path("."), Path(".spb/prompts/python-assistant.md"), harness="pi_agent"
    )
    monkeypatch.setattr("spb.fragment_eval.run_evaluation", fake_run)
    result = CliRunner().invoke(
        cli,
        [
            "eval",
            "ablate",
            ".spb/prompts/python-assistant.md",
            "--suite",
            ".spb/evals/python-assistant-hf.yaml",
            "--harness",
            "pi_agent",
            "--mode",
            "drop",
            "--fragments",
            "routing",
            "--repeats",
            "1",
            "--output",
            str(tmp_path / "out.yaml"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Exploratory result: fewer than three repeats" in result.output
    assert "metric majority failure: example/quality" in result.output
    assert (
        "baseline 1/1 pass (median 0.900); variant 0/1 pass (median 0.900)"
        in result.output
    )
    assert "Warning: equal scores have different pass flags" in result.output


def test_cli_shows_last_phase_when_judging_fails(monkeypatch, tmp_path: Path) -> None:
    from spb.cli import cli

    def failing_run(prompt, suite, *, suite_sha256, harness, on_progress):
        on_progress("case 1/17 'reads before editing': judging 'Prompt compliance'")
        raise ValueError("Evaluation LLM outputted an invalid JSON")

    monkeypatch.setattr("spb.fragment_eval.run_evaluation", failing_run)
    output = tmp_path / "no-report.yaml"
    result = CliRunner().invoke(
        cli,
        [
            "eval",
            "ablate",
            ".spb/prompts/python-assistant.md",
            "--suite",
            ".spb/evals/python-assistant-hf.yaml",
            "--harness",
            "pi_agent",
            "--mode",
            "drop",
            "--fragments",
            "routing",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code != 0
    assert (
        "baseline, repeat 1/3: case 1/17 'reads before editing': judging"
        in result.output
    )
    assert "invalid JSON" in result.output
    assert not output.exists()


def test_duplicate_suite_rejected_before_ablation_calls(monkeypatch, tmp_path):
    from spb.cli import cli

    suite = tmp_path / "suite.yaml"
    suite.write_text(
        "model: m\njudge_model: j\nmetrics:\n  - type: answer_relevancy\n"
        "tests:\n  - name: same\n    input: a\n  - name: same\n    input: b\n"
    )
    monkeypatch.setattr(
        "spb.fragment_eval.compress_prompt", lambda *a, **k: pytest.fail("compressed")
    )
    for extra in ([], ["--dry-run"]):
        result = CliRunner().invoke(
            cli,
            [
                "eval",
                "ablate",
                ".spb/prompts/python-assistant.md",
                "--suite",
                str(suite),
                "--harness",
                "pi_agent",
            ]
            + extra,
        )
        assert result.exit_code != 0
        assert "Duplicate case" in result.output


def test_checkpoint_survives_failure_and_retains_completed_runs(monkeypatch, tmp_path):
    from spb.cli import cli

    calls = []

    def fake(prompt, suite, *, suite_sha256, harness, on_progress):
        calls.append(1)
        if len(calls) == 5:
            raise ValueError("endpoint failed")
        return replace(
            _run(),
            prompt_sha256=hashlib.sha256(prompt.content.encode()).hexdigest(),
            suite_sha256=suite_sha256,
            model=suite.model,
        )

    monkeypatch.setattr("spb.fragment_eval.run_evaluation", fake)
    output = tmp_path / "out.yaml"
    output.write_text("old final")
    result = CliRunner().invoke(
        cli,
        [
            "eval",
            "ablate",
            ".spb/prompts/python-assistant.md",
            "--suite",
            ".spb/evals/python-assistant-hf.yaml",
            "--harness",
            "pi_agent",
            "--mode",
            "drop",
            "--fragments",
            "routing",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code != 0
    assert output.read_text() == "old final"
    partial = yaml.safe_load(Path(str(output) + ".partial").read_text())
    assert partial["status"] == "incomplete"
    assert len(partial["baseline_runs"]) == 3
    assert len(partial["variants"][0]["runs"]) == 1
    assert "outcome" not in partial["variants"][0]


def test_rate_variant_records_compression_provenance():
    prompt = render_prompt(
        Path("."), Path(".spb/prompts/python-assistant.md"), harness="pi_agent"
    )
    plan = plan_fragment_evaluation(
        prompt,
        cases=1,
        mode="both",
        aliases=("routing",),
        rates=(0.5,),
        compressor="none",
    )
    assert plan.variants[0].compression is None
    provenance = plan.variants[1].compression
    assert provenance["compressor"] == "none"
    assert provenance["settings"] == {"rate": 0.5}
    assert provenance["input_sha256"] == provenance["output_sha256"]


@pytest.mark.parametrize("interruption", [ValueError("failed"), KeyboardInterrupt()])
def test_checkpoint_baseline_failure(monkeypatch, tmp_path, interruption):
    from spb.cli import cli

    calls = []

    def fake(prompt, suite, *, suite_sha256, harness, on_progress):
        calls.append(1)
        if len(calls) == 2:
            raise interruption
        return replace(
            _run(),
            prompt_sha256=hashlib.sha256(prompt.content.encode()).hexdigest(),
            suite_sha256=suite_sha256,
            model=suite.model,
        )

    monkeypatch.setattr("spb.fragment_eval.run_evaluation", fake)
    output = tmp_path / "out.yaml"
    result = CliRunner().invoke(
        cli,
        [
            "eval",
            "ablate",
            ".spb/prompts/python-assistant.md",
            "--suite",
            ".spb/evals/python-assistant-hf.yaml",
            "--harness",
            "pi_agent",
            "--mode",
            "drop",
            "--fragments",
            "routing",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code != 0
    partial = yaml.safe_load(Path(str(output) + ".partial").read_text())
    assert len(partial["baseline_runs"]) == 1
    assert not partial["variants"][0]["runs"]
    assert "Partial report:" in result.output


def test_atomic_checkpoint_preserves_old_file_on_replace_error(monkeypatch, tmp_path):
    from spb.fragment_eval import write_fragment_checkpoint

    path = tmp_path / "report"
    path.write_text("old")

    def fail(*args):
        raise OSError("replace failed")

    monkeypatch.setattr("spb.fragment_eval.os.replace", fail)
    with pytest.raises(OSError, match="replace failed"):
        write_fragment_checkpoint({"test": 1}, path)
    assert path.read_text() == "old"
    assert list(tmp_path.iterdir()) == [path]


def test_checkpoint_failure_stops_evaluation(monkeypatch):
    prompt = render_prompt(
        Path("."), Path(".spb/prompts/python-assistant.md"), harness="pi_agent"
    )
    suite = load_evaluation_suite(Path(".spb/evals/python-assistant-hf.yaml"))
    plan = plan_fragment_evaluation(
        prompt, cases=len(suite.cases), mode="drop", aliases=("routing",)
    )
    calls = []

    def fake(prompt, suite, *, suite_sha256, harness):
        calls.append(1)
        return replace(
            _run(),
            prompt_sha256=hashlib.sha256(prompt.content.encode()).hexdigest(),
            suite_sha256=suite_sha256,
            model=suite.model,
        )

    monkeypatch.setattr("spb.fragment_eval.run_evaluation", fake)

    def fail(data):
        raise OSError("checkpoint failed")

    with pytest.raises(OSError, match="checkpoint failed"):
        evaluate_fragment_plan(
            plan, suite, suite_sha256="suite", harness="pi_agent", on_checkpoint=fail
        )
    assert len(calls) == 1


def test_complete_report_atomic_failure_keeps_checkpoint(monkeypatch, tmp_path):
    from spb.cli import cli

    def fake(prompt, suite, *, suite_sha256, harness, on_progress):
        return replace(
            _run(),
            prompt_sha256=hashlib.sha256(prompt.content.encode()).hexdigest(),
            suite_sha256=suite_sha256,
            model=suite.model,
        )

    monkeypatch.setattr("spb.fragment_eval.run_evaluation", fake)

    def fail(*args):
        raise OSError("final failed")

    monkeypatch.setattr("spb.cli.write_fragment_report", fail)
    output = tmp_path / "out.yaml"
    output.write_text("old")
    result = CliRunner().invoke(
        cli,
        [
            "eval",
            "ablate",
            ".spb/prompts/python-assistant.md",
            "--suite",
            ".spb/evals/python-assistant-hf.yaml",
            "--harness",
            "pi_agent",
            "--mode",
            "drop",
            "--fragments",
            "routing",
            "--repeats",
            "1",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code != 0
    assert output.read_text() == "old"
    partial = yaml.safe_load(Path(str(output) + ".partial").read_text())
    assert partial["variants"][0]["outcome"]["verdict"] == "INDETERMINATE"


def test_checkpoint_timestamps_and_compression_are_stable(monkeypatch):
    prompt = render_prompt(
        Path("."), Path(".spb/prompts/python-assistant.md"), harness="pi_agent"
    )
    suite = load_evaluation_suite(Path(".spb/evals/python-assistant-hf.yaml"))
    plan = plan_fragment_evaluation(
        prompt,
        cases=len(suite.cases),
        mode="rate",
        aliases=("routing",),
        rates=(0.5,),
        compressor="none",
        repeats=1,
    )
    monkeypatch.setattr(
        "spb.fragment_eval.run_evaluation",
        lambda prompt, suite, *, suite_sha256, harness: replace(
            _run(),
            prompt_sha256=hashlib.sha256(prompt.content.encode()).hexdigest(),
            suite_sha256=suite_sha256,
            model=suite.model,
        ),
    )
    snapshots = []
    report = evaluate_fragment_plan(
        plan,
        suite,
        suite_sha256="suite",
        harness="pi_agent",
        on_checkpoint=lambda data: snapshots.append(
            yaml.safe_load(yaml.safe_dump(data))
        ),
    )
    assert all(
        s["baseline_runs"][0]["timestamp"]
        == snapshots[0]["baseline_runs"][0]["timestamp"]
        for s in snapshots
    )
    assert (
        snapshots[-1]["variants"][0]["compression"]
        == report.outcomes[0]["compression"]
        == plan.variants[0].compression
    )
    assert (
        report.as_dict()["baseline_runs"][0]["timestamp"]
        == snapshots[0]["baseline_runs"][0]["timestamp"]
    )


def test_direct_ablation_rejects_duplicate_suite_before_runner(monkeypatch):
    prompt = render_prompt(
        Path("."), Path(".spb/prompts/python-assistant.md"), harness="pi_agent"
    )
    suite = load_evaluation_suite(Path(".spb/evals/python-assistant-hf.yaml"))
    suite = replace(suite, cases=(suite.cases[0], suite.cases[0]))
    plan = plan_fragment_evaluation(prompt, cases=2, mode="drop", aliases=("routing",))
    monkeypatch.setattr(
        "spb.fragment_eval.run_evaluation", lambda *a, **k: pytest.fail("model called")
    )
    with pytest.raises(ValueError, match="Duplicate case"):
        evaluate_fragment_plan(plan, suite, suite_sha256="suite", harness="pi_agent")


def test_rate_provenance_records_compressor_result_and_fragment_hashes(monkeypatch):
    from spb.compression import CompressionResult

    prompt = render_prompt(
        Path("."), Path(".spb/prompts/python-assistant.md"), harness="pi_agent"
    )
    monkeypatch.setattr(
        "spb.fragment_eval.compress_prompt",
        lambda content, compressor, *, rate: CompressionResult(
            "short", compressor, {"model": "stub", "rate": rate}
        ),
    )
    plan = plan_fragment_evaluation(
        prompt, cases=1, mode="rate", aliases=("routing",), rates=(0.3,)
    )
    assert plan.variants[0].compression == {
        "alias": "routing",
        "rate": 0.3,
        "compressor": "llmlingua",
        "settings": {"model": "stub", "rate": 0.3},
        "input_sha256": hashlib.sha256(
            prompt.rendered_fragments["routing"].encode()
        ).hexdigest(),
        "output_sha256": hashlib.sha256(b"short").hexdigest(),
    }
