"""Extract one version section from CHANGELOG.md for GitHub release notes."""

from __future__ import annotations

import argparse
from pathlib import Path


def release_notes(changelog: str, version: str) -> str:
    """Return the body of one versioned changelog section."""
    normalized_version = version.removeprefix("v")
    heading = f"## [{normalized_version}]"
    lines = changelog.splitlines()

    try:
        start = next(
            index for index, line in enumerate(lines) if line.startswith(heading)
        )
    except StopIteration as error:
        raise ValueError(
            f"Changelog has no section for {normalized_version}"
        ) from error

    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if lines[index].startswith("## ")
        ),
        len(lines),
    )
    notes = "\n".join(lines[start + 1 : end]).strip()
    if not notes:
        raise ValueError(f"Changelog section for {normalized_version} is empty")
    return notes + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--changelog", type=Path, default=Path("CHANGELOG.md"))
    arguments = parser.parse_args()

    notes = release_notes(
        arguments.changelog.read_text(encoding="utf-8"), arguments.version
    )
    if arguments.output is None:
        print(notes, end="")
    else:
        arguments.output.write_text(notes, encoding="utf-8")


if __name__ == "__main__":
    main()
