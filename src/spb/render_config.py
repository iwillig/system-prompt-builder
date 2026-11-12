"""Configured prompt render targets."""

from pathlib import Path
from typing import Any


def configured_renders(
    config: dict[str, Any], project_root: Path
) -> list[tuple[Path, str]]:
    """Parse configured render targets without requiring outputs to exist."""
    entries = config.get("renders", [])
    if not isinstance(entries, list):
        raise ValueError("renders must be a list of prompt/harness mappings")
    targets: list[tuple[Path, str]] = []
    outputs: set[tuple[str, str]] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"prompt", "harness"}:
            raise ValueError("Each render must contain only prompt and harness")
        prompt, harness = entry["prompt"], entry["harness"]
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Render prompt must be a non-empty path")
        path = Path(prompt)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Render prompt must be relative to the project root")
        if not isinstance(harness, str) or not harness.strip():
            raise ValueError("Render harness must be a non-empty string")
        supported = config.get("support_harness")
        if not isinstance(supported, list) or harness not in supported:
            raise ValueError(f"Render harness is not supported: {harness}")
        output = (harness, path.stem)
        if output in outputs:
            raise ValueError(f"Duplicate render output: {harness}/{path.stem}.md")
        outputs.add(output)
        targets.append((project_root / path, harness))
    return targets
