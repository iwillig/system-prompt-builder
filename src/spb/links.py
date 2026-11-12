"""Configuration for project artifact links."""

from pathlib import Path
from typing import Any


def configured_links(
    config: dict[str, Any], project_root: Path
) -> list[tuple[Path, Path]]:
    """Parse link definitions without requiring rendered sources to exist."""
    entries = config.get("links", [])
    if not isinstance(entries, list):
        raise ValueError("links must be a list of source/destination mappings")
    links: list[tuple[Path, Path]] = []
    destinations: set[Path] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"source", "destination"}:
            raise ValueError("Each link must contain only source and destination")
        paths = []
        for key in ("source", "destination"):
            value = entry[key]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"Link {key} must be a non-empty path")
            path = Path(value)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Link {key} must be relative to the project root")
            paths.append(project_root / path)
        source, destination = paths
        # Resolve the parent only: resolving the destination follows an existing link.
        identity = destination.parent.resolve() / destination.name
        if identity in destinations:
            raise ValueError(f"Duplicate link destination: {destination}")
        destinations.add(identity)
        links.append((source, destination))
    return links
