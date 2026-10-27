from pathlib import Path

import pytest

from spb.sections import extract_sections, validate_layout


def test_extracts_named_sections_preserving_markdown() -> None:
    body = """\
<identity>
You are a coding agent.

Work with A & B and A &amp; B, with “smart quotes” and an em dash — preserved.
{{#tools}}
- `{{name}}`: {{summary}}
{{/tools}}
</identity>

<rules>
1. Read before editing.
2. {{harness.name}} only.
</rules>
"""

    sections = extract_sections(body, Path("prompt.md"))

    assert list(sections) == ["identity", "rules"]
    assert sections["identity"] == (
        "You are a coding agent.\n\n"
        "Work with A & B and A &amp; B, with “smart quotes” "
        "and an em dash — preserved.\n"
        "{{#tools}}\n- `{{name}}`: {{summary}}\n{{/tools}}"
    )
    assert sections["rules"] == "1. Read before editing.\n2. {{harness.name}} only."


def test_extracts_system_prompt_style_sections() -> None:
    body = "".join(
        f"<{name}>\nContent of {name}.\n</{name}>\n\n"
        for name in (
            "identity",
            "tools",
            "rules",
            "routing",
            "schema",
            "facts",
            "goals",
            "output",
        )
    )

    sections = extract_sections(body, Path("system.md"))

    assert list(sections) == [
        "identity",
        "tools",
        "rules",
        "routing",
        "schema",
        "facts",
        "goals",
        "output",
    ]
    assert sections["schema"] == "Content of schema."


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (
            "<schema>\n```xml\n<tool>read</tool>\n```\n</schema>",
            "tags are reserved for sections",
        ),
        ("<identity>\nx\n</identity>\n<identity>\ny\n</identity>", "Duplicate section"),
        ("<Identity>\nx\n</Identity>", "Invalid section tag"),
        ("<tool-list>\nx\n</tool-list>", "Invalid section tag"),
        ('<identity role="lead">\nx\n</identity>', "Invalid section tag"),
        ("<identity>\nfoo\n</rules>", "Invalid prompt section"),
        ("<identity>\nfoo\n", "Unclosed prompt section"),
        ("Intro\n<identity>\nx\n</identity>", "Text outside prompt sections"),
        ("<!-- note -->\n<identity>\nx\n</identity>", "Unsupported XML markup"),
        ("<?pi data?>\n<identity>\nx\n</identity>", "Unsupported XML markup"),
        ("<!DOCTYPE root>\n<identity>\nx\n</identity>", "Text outside prompt sections"),
    ],
)
def test_rejects_invalid_markup(body: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        extract_sections(body, Path("prompt.md"))


def test_rejects_section_without_content() -> None:
    with pytest.raises(ValueError, match="at least one section"):
        extract_sections("\n\n", Path("prompt.md"))


def test_validate_layout_requires_each_section_exactly_once() -> None:
    sections = {"identity": "x", "rules": "y"}
    validate_layout(
        "<identity>\n{{{sections.identity}}}\n</identity>\n\n"
        "<rules>\n{{{sections.rules}}}\n</rules>\n",
        sections,
        Path("layout.md"),
    )

    with pytest.raises(ValueError, match="sections.identity"):
        validate_layout(
            "<rules>\n{{{sections.rules}}}\n</rules>\n", sections, Path("l")
        )
    with pytest.raises(ValueError, match="exactly once"):
        validate_layout(
            "{{{sections.identity}}}{{{sections.identity}}}{{{sections.rules}}}",
            sections,
            Path("l"),
        )
    with pytest.raises(ValueError, match="missing section"):
        validate_layout(
            "{{{sections.identity}}}{{{sections.rules}}}{{{sections.output}}}",
            sections,
            Path("l"),
        )


def test_strips_marker_newlines_and_keeps_author_blank_lines() -> None:
    body = "<rules>\n\nFirst.\n\nLast.\n\n</rules>"

    sections = extract_sections(body, Path("prompt.md"))

    assert sections["rules"] == "\nFirst.\n\nLast.\n"


def test_without_trailing_newline_removes_exactly_one() -> None:
    from spb.sections import without_trailing_newline

    assert without_trailing_newline("a\n") == "a"
    assert without_trailing_newline("a\n\n") == "a\n"
    assert without_trailing_newline("a") == "a"
