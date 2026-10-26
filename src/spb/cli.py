"""Click commands for System Prompt Builder."""

from __future__ import annotations

import hashlib
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

import click
import yaml

from spb.compression import CompressionResult, compress_prompt
from spb.evaluation import (
    compare_evaluation_runs,
    group_mean_scores,
    load_evaluation_suite,
    run_evaluation,
    write_evaluation_comparison,
    write_evaluation_run,
)
from spb.rendering import RenderedPrompt, ResolvedSkill, render_prompt, validate_project


@click.group()
def cli() -> None:
    """Compose reproducible system prompts."""


@cli.command()
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Directory containing .spb/config.yaml.",
)
def validate(project_root: Path) -> None:
    """Validate project configuration and every prompt."""
    try:
        prompt_paths = validate_project(project_root)
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Validated {len(prompt_paths)} prompt(s).")


@cli.command()
@click.argument("prompt", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--harness", required=True, help="Harness to render for.")
@click.option(
    "--var",
    "variable_pairs",
    multiple=True,
    metavar="NAME=VALUE",
    help="Template variable value; may be provided more than once.",
)
@click.option(
    "--replace-release", is_flag=True, help="Replace a changed prompt release."
)
@click.option("--compress", is_flag=True, help="Write a compressed prompt artifact.")
@click.option(
    "--compressor",
    type=click.Choice(["none", "llmlingua"]),
    default="llmlingua",
    show_default=True,
    help="Compressor to use with --compress.",
)
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Directory containing .spb/config.yaml.",
)
def render(
    prompt: Path,
    harness: str,
    variable_pairs: tuple[str, ...],
    replace_release: bool,
    compress: bool,
    compressor: str,
    project_root: Path,
) -> None:
    """Render PROMPT into a harness-specific build artifact."""
    try:
        result = render_prompt(
            project_root,
            prompt,
            harness=harness,
            variables=_parse_variables(variable_pairs),
        )
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error

    try:
        compression = compress_prompt(result.content, compressor) if compress else None
    except ValueError as error:
        raise click.ClickException(str(error)) from error

    output_path = project_root / "build" / harness / f"{prompt.stem}.md"
    manifest_path = output_path.with_suffix(".manifest.yaml")
    manifest = _manifest(prompt, harness, result, compression)
    try:
        replacing = _check_release_collision(
            output_path, manifest_path, manifest, replace_release
        )
    except (OSError, ValueError, yaml.YAMLError) as error:
        raise click.ClickException(str(error)) from error

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(output_path, result.content)
    compressed_path = output_path.with_suffix(".compressed.md")
    if compression is None:
        compressed_path.unlink(missing_ok=True)
    else:
        _atomic_write(compressed_path, compression.content)
    _atomic_write(manifest_path, yaml.safe_dump(manifest, sort_keys=False))
    _write_skills_lock(project_root, result.skills)
    if replacing:
        click.echo(f"Replacing release {result.name}@{result.version}", err=True)
    click.echo(output_path)


@cli.group()
def eval() -> None:
    """Run DeepEval suites against rendered system prompts."""


@eval.command("validate")
@click.argument("suite", type=click.Path(exists=True, path_type=Path))
def eval_validate(suite: Path) -> None:
    """Validate an evaluation SUITE without calling a model."""
    try:
        loaded = load_evaluation_suite(suite)
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(f"Validated {len(loaded.cases)} evaluation test(s).")


@eval.command("run")
@click.argument("prompt", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--suite", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--harness", required=True)
@click.option("--var", "variable_pairs", multiple=True, metavar="NAME=VALUE")
@click.option(
    "--dry-run", is_flag=True, help="Validate inputs without calling a model."
)
@click.option("--output", type=click.Path(path_type=Path))
@click.option("--fail-under", type=click.FloatRange(0, 1))
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
)
def eval_run(
    prompt: Path,
    suite: Path,
    harness: str,
    variable_pairs: tuple[str, ...],
    dry_run: bool,
    output: Path | None,
    fail_under: float | None,
    project_root: Path,
) -> None:
    """Run SUITE against direct model responses using PROMPT as the system prompt."""
    try:
        rendered = render_prompt(
            project_root,
            prompt,
            harness=harness,
            variables=_parse_variables(variable_pairs),
        )
        loaded_suite = load_evaluation_suite(suite)
        if not dry_run:
            evaluation_run = run_evaluation(
                rendered,
                loaded_suite,
                suite_sha256=_sha256(suite.read_text(encoding="utf-8")),
                harness=harness,
            )
            result_path = write_evaluation_run(
                evaluation_run,
                output
                or project_root
                / "build"
                / "evals"
                / rendered.name
                / rendered.version
                / "result.yaml",
            )
            if any(
                not metric["passed"]
                for case in evaluation_run.results
                for metric in case["metrics"]
            ):
                raise click.ClickException("One or more required metrics failed")
            if fail_under is not None and evaluation_run.mean_score < fail_under:
                raise click.ClickException(
                    f"Mean score {evaluation_run.mean_score:.3f} is below "
                    f"{fail_under:.3f}"
                )
            click.echo(result_path)
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    if dry_run:
        click.echo(f"Validated {len(loaded_suite.cases)} evaluation test(s).")


@eval.command("compare")
@click.argument("prompt", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--suite", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--harness", required=True)
@click.option("--var", "variable_pairs", multiple=True, metavar="NAME=VALUE")
@click.option(
    "--compressor", type=click.Choice(["none", "llmlingua"]), default="llmlingua"
)
@click.option(
    "--max-score-drop", default=0.0, type=click.FloatRange(0, 1), show_default=True
)
@click.option("--output", type=click.Path(path_type=Path))
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
)
def eval_compare(
    prompt: Path,
    suite: Path,
    harness: str,
    variable_pairs: tuple[str, ...],
    compressor: str,
    max_score_drop: float,
    output: Path | None,
    project_root: Path,
) -> None:
    """Compare normal and compressed PROMPT evaluation scores."""
    try:
        rendered = render_prompt(
            project_root,
            prompt,
            harness=harness,
            variables=_parse_variables(variable_pairs),
        )
        compressed = compress_prompt(rendered.content, compressor)
        loaded_suite = load_evaluation_suite(suite)
        suite_sha256 = _sha256(suite.read_text(encoding="utf-8"))
        baseline = run_evaluation(
            rendered, loaded_suite, suite_sha256=suite_sha256, harness=harness
        )
        candidate = run_evaluation(
            replace(rendered, content=compressed.content),
            loaded_suite,
            suite_sha256=suite_sha256,
            harness=harness,
        )
        comparison = compare_evaluation_runs(
            baseline, candidate, max_score_drop=max_score_drop
        )
        result_path = write_evaluation_comparison(
            comparison,
            output
            or project_root
            / "build"
            / "evals"
            / rendered.name
            / rendered.version
            / "comparison.yaml",
        )
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(result_path)
    if not comparison.passed:
        raise click.ClickException(
            f"Compressed prompt score dropped by {comparison.score_drop:.3f}"
        )


@cli.group()
def benchmark() -> None:
    """Run versioned prompt benchmarks with DeepEval."""


@benchmark.command("run")
@click.argument("prompt", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--suite", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--harness", required=True)
@click.option("--var", "variable_pairs", multiple=True, metavar="NAME=VALUE")
@click.option("--output", type=click.Path(path_type=Path))
@click.option("--fail-under", type=click.FloatRange(0, 1))
@click.option(
    "--min-group-score", "minimum_groups", multiple=True, metavar="GROUP=SCORE"
)
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
)
def benchmark_run(
    prompt: Path,
    suite: Path,
    harness: str,
    variable_pairs: tuple[str, ...],
    output: Path | None,
    fail_under: float | None,
    minimum_groups: tuple[str, ...],
    project_root: Path,
) -> None:
    """Benchmark PROMPT and persist per-scenario-group scores."""
    try:
        rendered = render_prompt(
            project_root,
            prompt,
            harness=harness,
            variables=_parse_variables(variable_pairs),
        )
        loaded_suite = load_evaluation_suite(suite)
        evaluation_run = run_evaluation(
            rendered,
            loaded_suite,
            suite_sha256=_sha256(suite.read_text(encoding="utf-8")),
            harness=harness,
        )
        minimums = _parse_score_limits(minimum_groups, "--min-group-score")
        groups = group_mean_scores(evaluation_run)
        _check_minimum_scores(groups, minimums, "benchmark group")
        if fail_under is not None and evaluation_run.mean_score < fail_under:
            raise ValueError(
                f"Mean score {evaluation_run.mean_score:.3f} is below {fail_under:.3f}"
            )
        result_path = write_evaluation_run(
            evaluation_run,
            output
            or project_root
            / "build"
            / "benchmarks"
            / rendered.name
            / rendered.version
            / "result.yaml",
        )
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(result_path)


@benchmark.command("compare")
@click.argument(
    "baseline", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.argument(
    "candidate", type=click.Path(exists=True, dir_okay=False, path_type=Path)
)
@click.option("--suite", required=True, type=click.Path(exists=True, path_type=Path))
@click.option("--harness", required=True)
@click.option("--var", "variable_pairs", multiple=True, metavar="NAME=VALUE")
@click.option("--max-score-drop", default=0.0, type=click.FloatRange(0, 1))
@click.option(
    "--max-group-score-drop",
    "maximum_group_drops",
    multiple=True,
    metavar="GROUP=SCORE",
)
@click.option("--output", type=click.Path(path_type=Path))
@click.option(
    "--project-root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=Path("."),
)
def benchmark_compare(
    baseline: Path,
    candidate: Path,
    suite: Path,
    harness: str,
    variable_pairs: tuple[str, ...],
    max_score_drop: float,
    maximum_group_drops: tuple[str, ...],
    output: Path | None,
    project_root: Path,
) -> None:
    """Compare BASELINE and CANDIDATE prompt source versions."""
    try:
        variables = _parse_variables(variable_pairs)
        baseline_prompt = render_prompt(
            project_root, baseline, harness=harness, variables=variables
        )
        candidate_prompt = render_prompt(
            project_root, candidate, harness=harness, variables=variables
        )
        loaded_suite = load_evaluation_suite(suite)
        suite_sha256 = _sha256(suite.read_text(encoding="utf-8"))
        baseline_run = run_evaluation(
            baseline_prompt, loaded_suite, suite_sha256=suite_sha256, harness=harness
        )
        candidate_run = run_evaluation(
            candidate_prompt, loaded_suite, suite_sha256=suite_sha256, harness=harness
        )
        comparison = compare_evaluation_runs(
            baseline_run, candidate_run, max_score_drop=max_score_drop
        )
        maximums = _parse_score_limits(maximum_group_drops, "--max-group-score-drop")
        _check_maximum_drops(comparison.group_score_drops, maximums)
        result_path = write_evaluation_comparison(
            comparison,
            output
            or project_root
            / "build"
            / "benchmarks"
            / candidate_prompt.name
            / candidate_prompt.version
            / "comparison.yaml",
        )
    except (OSError, ValueError) as error:
        raise click.ClickException(str(error)) from error
    click.echo(result_path)
    if not comparison.passed:
        raise click.ClickException(
            f"Prompt score dropped by {comparison.score_drop:.3f}"
        )


@cli.command()
@click.argument("source", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.argument("destination", type=click.Path(path_type=Path))
@click.option("--replace", is_flag=True, help="Replace an existing destination.")
def link(source: Path, destination: Path, replace: bool) -> None:
    """Create a symlink from DESTINATION to compiled SOURCE."""
    if destination.exists() or destination.is_symlink():
        if not replace:
            raise click.ClickException(
                "Destination already exists; use --replace to replace it"
            )
        destination.unlink()
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(source.resolve())
    except OSError as error:
        raise click.ClickException(f"Unable to create symlink: {error}") from error
    click.echo(destination)


def _parse_score_limits(values: tuple[str, ...], option: str) -> dict[str, float]:
    limits: dict[str, float] = {}
    for value in values:
        group, separator, score_text = value.partition("=")
        if not separator or not group:
            raise ValueError(f"{option} must use GROUP=SCORE")
        try:
            score = float(score_text)
        except ValueError as error:
            raise ValueError(f"{option} score must be a number") from error
        if not 0 <= score <= 1:
            raise ValueError(f"{option} score must be between 0 and 1")
        if group in limits:
            raise ValueError(f"Duplicate {option} group: {group}")
        limits[group] = score
    return limits


def _check_minimum_scores(
    actual_scores: dict[str, float], minimums: dict[str, float], label: str
) -> None:
    for group, minimum in minimums.items():
        if group not in actual_scores:
            raise ValueError(f"Unknown {label}: {group}")
        if actual_scores[group] < minimum:
            raise ValueError(
                f"{label.capitalize()} {group} score {actual_scores[group]:.3f} "
                f"is below {minimum:.3f}"
            )


def _check_maximum_drops(drops: dict[str, float], maximums: dict[str, float]) -> None:
    for group, maximum in maximums.items():
        if group not in drops:
            raise ValueError(f"Unknown benchmark group: {group}")
        if drops[group] > maximum:
            raise ValueError(
                f"Benchmark group {group} score dropped by {drops[group]:.3f}"
            )


def _parse_variables(variable_pairs: tuple[str, ...]) -> dict[str, str]:
    variables: dict[str, str] = {}
    for pair in variable_pairs:
        name, separator, value = pair.partition("=")
        if not separator or not name:
            raise ValueError("--var must use NAME=VALUE")
        if not name.isidentifier():
            raise ValueError(f"Invalid --var name: {name}")
        if name in {"harness", "tools"}:
            raise ValueError(f"Reserved --var name: {name}")
        if name in variables:
            raise ValueError(f"Duplicate --var name: {name}")
        variables[name] = value
    return variables


def _write_skills_lock(project_root: Path, skills: tuple[ResolvedSkill, ...]) -> None:
    lock_path = project_root / ".spb" / "skills.lock.yaml"
    existing = (
        yaml.safe_load(lock_path.read_text(encoding="utf-8"))
        if lock_path.exists()
        else {}
    )
    if not isinstance(existing, dict):
        raise ValueError("Existing skills lockfile must be a YAML mapping")
    providers = existing.setdefault("providers", {})
    if not isinstance(providers, dict):
        raise ValueError("Existing skills lockfile providers must be a mapping")

    for provider_name in {skill.provider for skill in skills if skill.gitrepo}:
        provider_skills = [skill for skill in skills if skill.provider == provider_name]
        first = provider_skills[0]
        providers[provider_name] = {
            "gitrepo": first.gitrepo,
            "revision": first.revision,
            "skills": [
                {
                    "reference": skill.reference,
                    "path": str(skill.path),
                    "sha256": skill.sha256,
                }
                for skill in provider_skills
            ],
        }
    _atomic_write(lock_path, yaml.safe_dump(existing, sort_keys=False))


def _check_release_collision(
    output_path: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    replace_release: bool,
) -> bool:
    if not output_path.exists() and not manifest_path.exists():
        return False
    if not manifest_path.exists():
        if replace_release:
            return True
        raise ValueError(
            "Existing artifact has no readable manifest; use --replace-release"
        )

    existing = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(existing, dict):
        raise ValueError(
            "Existing artifact has no readable manifest; use --replace-release"
        )
    same_identity = all(
        existing.get(key) == manifest[key] for key in ("name", "version", "harness")
    )
    changed = bool(existing.get("rendered_sha256") != manifest["rendered_sha256"])
    if same_identity and changed:
        if replace_release:
            return True
        raise ValueError(
            "Prompt release collision; use --replace-release to replace it"
        )
    if changed and not replace_release:
        raise ValueError(
            "Existing artifact differs; use --replace-release to replace it"
        )
    return changed


def _atomic_write(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def _manifest(
    prompt: Path,
    harness: str,
    result: RenderedPrompt,
    compression: CompressionResult | None,
) -> dict[str, Any]:
    visible_variables, redacted_variables = _redact_variables(result.variables)
    manifest: dict[str, Any] = {
        "name": result.name,
        "version": result.version,
        "source": str(prompt),
        "source_sha256": _sha256(prompt.read_text(encoding="utf-8")),
        "harness": harness,
        "rendered_sha256": _sha256(result.content),
        "variables": visible_variables,
        "redacted_variables": redacted_variables,
        "skills": [
            {
                "reference": skill.reference,
                "path": str(skill.path),
                "sha256": skill.sha256,
            }
            for skill in result.skills
        ],
    }
    if compression is not None:
        manifest["compression"] = {
            "compressor": compression.compressor,
            "settings": compression.settings,
            "sha256": _sha256(compression.content),
        }
    return manifest


def _redact_variables(variables: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    secret_words = ("password", "secret", "token", "key")
    visible: dict[str, Any] = {}
    redacted: list[str] = []
    for name, value in variables.items():
        if any(word in name.lower() for word in secret_words):
            redacted.append(name)
        else:
            visible[name] = value
    return visible, redacted


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
