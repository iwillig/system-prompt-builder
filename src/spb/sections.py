"""Read pseudo-XML prompt sections from a Markdown body without XML escaping."""

from __future__ import annotations

import re
from pathlib import Path

from sloppy_xml import (
    Comment,
    EndElement,
    EntityRef,
    ParseError,
    ProcessingInstruction,
    RecoveryStrategy,
    StartElement,
    Text,
    stream_parse,
)

SECTION_NAME = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")
SECTION_SLOT = re.compile(r"\{\{\{sections\.([a-z][a-z0-9]*(?:_[a-z0-9]+)*)\}\}\}")


def extract_sections(body: str, path: Path) -> dict[str, str]:
    """Extract top-level sections, preserving their Markdown text.

    Section names must use lowercase snake_case. One newline directly after the
    opening tag and one directly before the closing tag are treated as marker
    placement rather than content. All other whitespace, blank lines, literal
    ampersands, and entity references are preserved. XML-like tags, attributes,
    comments, processing instructions, and entity-reference events are rejected
    so section values stay readable Markdown instead of escaped XML.
    """
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for event in stream_parse(
        body,
        preserve_whitespace=True,
        resolve_entities=False,
        recovery_strategy=RecoveryStrategy.STRICT,
        recover=False,
        auto_close_tags=False,
        fix_encoding=False,
        smart_quotes=False,
        repair_attributes=False,
        emit_errors=True,
    ):
        location = f"{path} (body line {event.line}, column {event.column})"
        if isinstance(event, ParseError):
            raise ValueError(f"Invalid prompt section at {location}: {event.message}")
        if isinstance(event, StartElement):
            if current is not None:
                raise ValueError(
                    f"Unexpected XML-like tag <{event.name}> inside <{current}> "
                    f"at {location}; tags are reserved for sections"
                )
            if not SECTION_NAME.fullmatch(event.name) or event.attrs:
                raise ValueError(f"Invalid section tag <{event.name}> at {location}")
            if event.name in sections:
                raise ValueError(f"Duplicate section <{event.name}> at {location}")
            sections[event.name] = []
            current = event.name
        elif isinstance(event, EndElement):
            if current != event.name or event.auto_closed:
                raise ValueError(
                    f"Unexpected closing tag </{event.name}> at {location}"
                )
            current = None
        elif isinstance(event, Text):
            if current is None:
                if event.content.strip():
                    raise ValueError(f"Text outside prompt sections at {location}")
            else:
                sections[current].append(event.content)
        elif isinstance(event, (Comment, ProcessingInstruction, EntityRef)):
            raise ValueError(f"Unsupported XML markup at {location}")
    if current is not None:
        raise ValueError(f"Unclosed prompt section <{current}> in {path}")
    if not sections:
        raise ValueError(f"Prompt {path} must contain at least one section")
    return {
        name: _without_boundary_newline("".join(parts))
        for name, parts in sections.items()
    }


def _without_boundary_newline(value: str) -> str:
    if value.startswith("\n"):
        value = value[1:]
    if value.endswith("\n"):
        value = value[:-1]
    return value


def without_trailing_newline(value: str) -> str:
    """Remove one trailing newline from a rendered section value.

    Mustache keeps the terminator of a section value's last line. Layouts own
    the newline before each closing marker, so insertion removes that one
    artifact newline instead of the layout adding a blank line.
    """
    return value[:-1] if value.endswith("\n") else value


def validate_layout(layout: str, sections: dict[str, str], path: Path) -> None:
    """Require each section to have exactly one unescaped layout slot."""
    slots = SECTION_SLOT.findall(layout)
    for name in sections:
        if slots.count(name) != 1:
            raise ValueError(
                f"Layout {path} must include {{{{{{sections.{name}}}}}}} exactly once"
            )
    for name in slots:
        if name not in sections:
            raise ValueError(f"Layout {path} references missing section <{name}>")
