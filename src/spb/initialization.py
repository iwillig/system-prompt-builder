"""Create the starter files for a System Prompt Builder project."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class InitializedProject:
    """Paths created for a new prompt project."""

    root: Path
    config: Path
    prompt: Path
    skills: Path


def initialize_project(project_root: Path, *, harness: str) -> InitializedProject:
    """Create a minimal project without overwriting managed files."""
    normalized_harness = harness.strip()
    if not normalized_harness:
        raise ValueError("Harness name cannot be empty")

    root = project_root.resolve()
    config_path = root / ".spb" / "config.yaml"
    prompt_path = root / "prompts" / "project-assistant.md"
    skills_path = root / "skills" / "local"
    managed_files = (config_path, prompt_path)
    conflicts = [path for path in managed_files if path.exists() or path.is_symlink()]
    if conflicts:
        relative_conflicts = ", ".join(
            str(path.relative_to(root)) for path in conflicts
        )
        raise ValueError(
            f"Project already contains managed files: {relative_conflicts}"
        )

    config = {
        "version": 1,
        "project-name": root.name or "System Prompt Project",
        "support-harness": [normalized_harness],
        "tool-provider-metadata": {normalized_harness: {"tools": []}},
        "skill-providers": [{"name": "local", "type": "local", "path": "skills/local"}],
    }
    prompt = """\
---
name: Project assistant
version: 1.0.0
skills: []
---
You are a coding agent running in {{harness.name}}.

Read the relevant project files before making changes.
Run the checks that cover your changes.
"""

    config_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    skills_path.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    prompt_path.write_text(prompt, encoding="utf-8")

    return InitializedProject(
        root=root,
        config=config_path,
        prompt=prompt_path,
        skills=skills_path,
    )
