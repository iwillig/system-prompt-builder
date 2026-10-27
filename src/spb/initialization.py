"""Create the starter files for a System Prompt Builder project."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class InitializedProject:
    """Paths created for a new prompt project."""

    root: Path
    config: Path
    prompt: Path
    layout: Path
    fragment: Path
    skills: Path


def initialize_project(project_root: Path, *, harness: str) -> InitializedProject:
    """Create a minimal project without overwriting managed files."""
    normalized_harness = harness.strip()
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*", normalized_harness):
        raise ValueError("Harness name must use snake_case")

    root = project_root.resolve()
    config_path = root / ".spb" / "config.yaml"
    prompt_path = root / ".spb" / "prompts" / "project-assistant.md"
    layout_path = root / ".spb" / "layouts" / "project-assistant.md"
    fragment_path = root / ".spb" / "fragments" / "project_instructions" / "FRAGMENT.md"
    skills_path = root / ".spb" / "skills" / "local"
    managed_files = (config_path, prompt_path, layout_path, fragment_path)
    conflicts = [path for path in managed_files if path.exists() or path.is_symlink()]
    fragment_dir = fragment_path.parent
    if (
        fragment_dir.exists() or fragment_dir.is_symlink()
    ) and fragment_path not in conflicts:
        conflicts.append(fragment_dir)
    if conflicts:
        relative_conflicts = ", ".join(
            str(path.relative_to(root)) for path in conflicts
        )
        raise ValueError(
            f"Project already contains managed files: {relative_conflicts}"
        )

    project_name = re.sub(r"[^a-z0-9]+", "_", root.name.lower()).strip("_")
    project_name = re.sub(r"^[^a-z]+", "", project_name)
    config = {
        "version": 1,
        "project_name": project_name or "system_prompt_project",
        "support_harness": [normalized_harness],
        "tool_provider_metadata": {normalized_harness: {"tools": []}},
        "skill_providers": [
            {"name": "local", "type": "local", "path": ".spb/skills/local"}
        ],
    }
    prompt = """\
---
name: Project assistant
version: 1.0.0
layout: .spb/layouts/project-assistant.md
fragments:
  instructions: .spb/fragments/project_instructions
skills: []
---
"""
    layout = "{{{fragments.instructions}}}\n"
    fragment = """\
You are a coding agent running in {{harness.name}}.

Read the relevant project files before making changes.
Run the checks that cover your changes.
"""

    config_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    layout_path.parent.mkdir(parents=True, exist_ok=True)
    fragment_dir.mkdir(parents=True, exist_ok=True)
    skills_path.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    prompt_path.write_text(prompt, encoding="utf-8")
    layout_path.write_text(layout, encoding="utf-8")
    fragment_path.write_text(fragment, encoding="utf-8")

    return InitializedProject(
        root=root,
        config=config_path,
        prompt=prompt_path,
        layout=layout_path,
        fragment=fragment_path,
        skills=skills_path,
    )
