import pytest

from spb.release_notes import release_notes


def test_release_notes_extracts_the_requested_version() -> None:
    changelog = """\
# Changelog

## [Unreleased]

## [0.1.2] - 2026-10-26

### Changed

- Improved installation guidance.

## [0.1.1] - 2026-10-26

### Added

- Published the package.
"""

    assert release_notes(changelog, "v0.1.2") == (
        "### Changed\n\n- Improved installation guidance.\n"
    )


def test_release_notes_rejects_an_unknown_version() -> None:
    with pytest.raises(ValueError, match="no section"):
        release_notes("# Changelog\n", "v9.9.9")
