"""Public prompt-composition API."""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chevron
import yaml


@dataclass(frozen=True)
class ResolvedSkill:
    """A local skill resolved during prompt composition."""

    reference: str
    path: Path
    content: str
    provider: str
    gitrepo: str | None = None
    revision: str | None = None

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RenderedPrompt:
    """The user-visible result of composing a prompt for one harness."""

    name: str
    version: str
    content: str
    variables: dict[str, Any]
    skills: tuple[ResolvedSkill, ...]


def render_prompt(
    project_root: Path,
    prompt_path: Path,
    *,
    harness: str,
    variables: dict[str, str] | None = None,
) -> RenderedPrompt:
    """Render a Markdown prompt with its local skills and harness metadata."""
    config = _load_yaml(project_root / ".spb" / "config.yaml")
    metadata, body = _read_prompt(prompt_path)
    tools = _tools_for_harness(config, harness)
    resolved_variables = _resolve_variables(metadata, variables or {})
    rendered_body = chevron.render(
        body,
        {"harness": {"name": harness}, "tools": tools, **resolved_variables},
    ).rstrip()
    skills = tuple(
        _resolve_skill(config, project_root, skill) for skill in _skills(metadata)
    )
    content = rendered_body + (
        "\n\n" + "\n\n".join(skill.content for skill in skills) if skills else "\n"
    )
    return RenderedPrompt(
        name=_required_string(metadata, "name"),
        version=_semantic_version(metadata),
        content=content,
        variables=resolved_variables,
        skills=skills,
    )


def validate_project(project_root: Path) -> list[Path]:
    """Validate every prompt in the project's prompts directory."""
    config = _load_yaml(project_root / ".spb" / "config.yaml")
    harnesses = _supported_harnesses(config)
    prompt_paths = sorted((project_root / "prompts").glob("**/*.md"))
    _tools_for_harness(config, harnesses[0])
    for prompt_path in prompt_paths:
        metadata, _ = _read_prompt(prompt_path)
        _required_string(metadata, "name")
        _semantic_version(metadata)
        _variable_declarations(metadata)
        for skill in _skills(metadata):
            _resolve_skill(config, project_root, skill)
    return prompt_paths


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return loaded


def _read_prompt(path: Path) -> tuple[dict[str, Any], str]:
    source = path.read_text(encoding="utf-8")
    if not source.startswith("---\n"):
        raise ValueError(f"Prompt {path} must begin with YAML front matter")
    _, front_matter, body = source.split("---\n", maxsplit=2)
    metadata = yaml.safe_load(front_matter)
    if not isinstance(metadata, dict):
        raise ValueError(f"Prompt {path} front matter must be a YAML mapping")
    return metadata, body


def _supported_harnesses(config: dict[str, Any]) -> list[str]:
    harnesses = config.get("support-harness")
    if not isinstance(harnesses, list) or not harnesses:
        raise ValueError("Project configuration must define support-harness")
    if not all(isinstance(harness, str) for harness in harnesses):
        raise ValueError("support-harness must contain harness names")
    return harnesses


def _tools_for_harness(config: dict[str, Any], harness: str) -> list[dict[str, str]]:
    metadata = config.get("tool-provider-metadata")
    if not isinstance(metadata, dict) or not isinstance(metadata.get(harness), dict):
        raise ValueError(f"Unsupported harness: {harness}")
    tools = metadata[harness].get("tools", [])
    if not isinstance(tools, list) or not all(isinstance(tool, dict) for tool in tools):
        raise ValueError(f"Harness {harness} has invalid tool metadata")
    return tools


def _skills(metadata: dict[str, Any]) -> list[str]:
    skills = metadata.get("skills", [])
    if not isinstance(skills, list) or not all(
        isinstance(skill, str) for skill in skills
    ):
        raise ValueError("Prompt skills must be a list of provider-qualified names")
    return skills


def _resolve_skill(
    config: dict[str, Any], project_root: Path, reference: str
) -> ResolvedSkill:
    provider_name, separator, skill_name = reference.partition("/")
    if not separator or not provider_name or not skill_name:
        raise ValueError(f"Invalid skill reference: {reference}")
    providers = config.get("skill-providers")
    if not isinstance(providers, list):
        raise ValueError("Project configuration must define skill-providers")
    provider = next(
        (
            candidate
            for candidate in providers
            if isinstance(candidate, dict) and candidate.get("name") == provider_name
        ),
        None,
    )
    if not isinstance(provider, dict):
        raise ValueError(f"Unsupported skill provider: {provider_name}")
    provider_type = provider.get("type")
    if provider_type == "local":
        path = provider.get("path")
        if not isinstance(path, str):
            raise ValueError(f"Local provider {provider_name} must define a path")
        skill_path = project_root / path / f"{skill_name}.md"
        return ResolvedSkill(
            reference=reference,
            path=skill_path,
            content=skill_path.read_text(encoding="utf-8"),
            provider=provider_name,
        )
    if provider_type == "git":
        return _resolve_git_skill(
            project_root, provider_name, provider, reference, skill_name
        )
    raise ValueError(f"Unsupported skill provider: {provider_name}")


def _resolve_git_skill(
    project_root: Path,
    provider_name: str,
    provider: dict[str, Any],
    reference: str,
    skill_name: str,
) -> ResolvedSkill:
    gitrepo = provider.get("gitrepo")
    revision = provider.get("revision")
    skill_root = provider.get("skill-root")
    if not isinstance(gitrepo, str) or not isinstance(skill_root, str):
        raise ValueError(
            f"Git provider {provider_name} must define gitrepo and skill-root"
        )
    if not isinstance(revision, str) or not re.fullmatch(
        r"[0-9a-fA-F]{40,64}", revision
    ):
        raise ValueError(
            f"Git provider {provider_name} must define a pinned commit SHA"
        )

    cache_path = project_root / ".spb" / "cache" / provider_name
    if not cache_path.exists():
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        _run_git("clone", "--quiet", "--no-checkout", gitrepo, str(cache_path))
    else:
        _run_git("-C", str(cache_path), "fetch", "--quiet", "origin", revision)
    _run_git("-C", str(cache_path), "checkout", "--quiet", "--detach", revision)
    skill_path = cache_path / skill_root / f"{skill_name}.md"
    return ResolvedSkill(
        reference=reference,
        path=skill_path,
        content=skill_path.read_text(encoding="utf-8"),
        provider=provider_name,
        gitrepo=gitrepo,
        revision=revision,
    )


def _run_git(*arguments: str) -> None:
    try:
        subprocess.run(["git", *arguments], check=True, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise ValueError("Git is required to resolve git skill providers") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip()
        raise ValueError(f"Git skill provider resolution failed: {detail}") from error


def _resolve_variables(
    metadata: dict[str, Any], supplied: dict[str, str]
) -> dict[str, Any]:
    declarations = _variable_declarations(metadata)
    resolved: dict[str, Any] = {}
    for name, declaration in declarations.items():
        if name in supplied:
            resolved[name] = supplied[name]
        elif "default" in declaration:
            resolved[name] = declaration["default"]
        else:
            raise ValueError(f"Missing required prompt variable: {name}")

    unknown = set(supplied) - set(declarations)
    if unknown:
        raise ValueError(f"Undeclared prompt variable: {sorted(unknown)[0]}")
    return resolved


def _variable_declarations(metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    declarations = metadata.get("variables", {})
    if not isinstance(declarations, dict):
        raise ValueError("Prompt variables must be a mapping")

    validated: dict[str, dict[str, Any]] = {}
    reserved = {"harness", "tools"}
    for name, declaration in declarations.items():
        if not isinstance(name, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", name
        ):
            raise ValueError(f"Invalid prompt variable name: {name}")
        if name in reserved:
            raise ValueError(f"Prompt variable name is reserved: {name}")
        if not isinstance(declaration, dict):
            raise ValueError(f"Variable {name} must be a mapping")

        has_required = declaration.get("required") is True
        has_default = "default" in declaration
        if set(declaration) - {"required", "default"} or has_required == has_default:
            raise ValueError(
                f"Variable {name} must define exactly one of required: true or default"
            )
        if "required" in declaration and declaration["required"] is not True:
            raise ValueError(f"Variable {name} required must be true")
        validated[name] = declaration
    return validated


def _semantic_version(metadata: dict[str, Any]) -> str:
    version = _required_string(metadata, "version")
    semver = re.compile(
        r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
        r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
    )
    if not semver.fullmatch(version):
        raise ValueError("Prompt front matter must define a semantic version")
    return version


def _required_string(metadata: dict[str, Any], name: str) -> str:
    value = metadata.get(name)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Prompt front matter must define {name}")
    return value
