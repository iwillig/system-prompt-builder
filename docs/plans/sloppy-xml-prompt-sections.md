# Plan: prompt sections with Sloppy XML and Mustache

**Status:** implemented. Literal XML-like tags are reserved for structure.
**Research:** [strict XML alternative](../research/xml-prompt-values.md).
**Question:** can SPB turn the sections in `../symbolic-tools/SYSTEM.md` into
Mustache variables without making authors write CDATA or escaped Markdown?

## Proposed source and output

Keep YAML front matter for release metadata and declared variables. Treat the
Markdown body as a sequence of named, top-level, XML-like sections. A prompt
source could look like this:

````markdown
---
name: Symbolic assistant
version: 1.0.0
skills: []
variables:
  project_name:
    required: true
---
<identity>
You are a coding agent for {{{project_name}}}.
</identity>

<rules>
1. Work in {{harness.name}}.
2. Read source before changing it.
</rules>

<schema>
```prolog
defines(Function, Arity, Params, File, Line)
```
</schema>
````

The Prolog fence is ordinary Markdown inside the section value. The section names from the reference prompt are
`identity`, `tools`, `rules`, `routing`, `schema`, `facts`, `goals`, and `output`.
Sections can be absent. Each accepted section name is unique; the document
order is not the output contract. SPB should report an error for duplicates,
unknown structural tags, missing closing tags, and non-whitespace content outside sections.
These constraints are **proposed SPB rules**, not guarantees from Sloppy XML.
[Reference prompt][reference-prompt] [Sloppy XML parser][parser]

Render each section once with the existing Mustache context (harness name,
configured tool list, and declared variables). Supply the rendered strings under
a separate `sections` key to a layout template. For example:

```mustache
<identity>
{{{sections.identity}}}
</identity>

<rules>
{{{sections.rules}}}
</rules>
```

This leaves `tools` available as the existing list for `{{#tools}}` inside a
section while `sections.tools` means the complete tools-section string. Triple
Mustache preserves plain-text values; ordinary Mustache interpolation would
HTML-escape them. Mustache does not expand tags inside an interpolated value,
so render the section content first and the layout second. The output remains
plain text, including any section markers in the layout. [SPB renderer][renderer]
[Mustache interpolation][mustache]

## Parser evidence and a hard limit

The linked package is `sloppy-xml` (import `sloppy_xml`), version 0.3.1 in its
project metadata. It offers `stream_parse()` events and `tree_parse()` built on
an ElementTree builder. Its default options recover malformed tags, resolve
entities, and omit whitespace-only text. Its tree builder ignores parse-error
events and returns the first root, so `tree_parse()` alone is not a validator
for prompt sources. The project README warns that the library is experimental
and that its author cannot vouch for its quality. [README][readme]
[Parser source][parser] [Package metadata][package]

A local, isolated probe of 0.3.1 showed:

| Input within a section | Observed behavior |
| --- | --- |
| `A & B` | Default tree parsing returned `A & B`, but streaming with `resolve_entities=False` and lenient recovery changed the text to `A &amp; B` and emitted a warning. |
| `A &amp; B` | Default tree parsing returned `A & B`. |
| `<tool>read</tool>` inside a Markdown code fence | The parser emitted `StartElement(tool)` and `EndElement(tool)`; tree `.text` contained only the text before `<tool>`. |
| Two top-level `<identity>` elements | Tree parsing returned only the first root. |
| Mustache tags such as `{{#tools}}` | They appeared as ordinary text. |
| `../symbolic-tools/SYSTEM.md` with strict streaming but default `fix_encoding=True` | Eight sections appeared, but an `encoding_fix` error reported a punctuation substitution. Setting `fix_encoding=False` produced all eight sections without parse errors. |

These observations match the source's tag regex, recovery settings, and tree
builder behavior. They mean **the library does not, by itself, preserve arbitrary
Markdown as a section value**. In particular, a fenced XML snippet is still
recognized as markup. [Parser source][parser]

## Parser seam

A source reader should expose one interface to the renderer: read a source file
and return validated metadata plus an ordered mapping of section names to
unmodified Markdown text. The Sloppy XML adapter would be behind this seam,
not a new set of special cases in every CLI command. `render_prompt()` and
`validate_project()` already meet at `_read_prompt()`. [SPB renderer][renderer]

The implemented reader lives in `src/spb/sections.py` and is called by
`render_prompt()` and `validate_project()`. Use `stream_parse()` with
`preserve_whitespace=True`,
`resolve_entities=False`, `recovery_strategy=STRICT`, `recover=False`,
`auto_close_tags=False`, `fix_encoding=False`, `smart_quotes=False`,
`repair_attributes=False`, and `emit_errors=True`. Track a stack of allowed
section tags and reject every `ParseError`; do not trust automatic recovery or
`tree_parse()` to preserve content. The user chose to reserve XML-like tags for
structure, including inside Markdown fences. Reject unexpected tags with a
clear diagnostic rather than silently changing the text. Literal `&` stays
literal with the strict, non-resolving parser settings in the isolated probe;
`&amp;` also remains literal text. These settings still need end-to-end tests
against actual prompt files. [Parser source][parser]

Keep layout rendering separate from section extraction. The layout is a
per-prompt Markdown file under `.spb/layouts/`, selected by front-matter
`layout`. Every section must appear exactly once as a
`{{{sections.<name>}}}` slot, and a layout may not reference a missing
section, so missing sections fail rather than render empty. One newline
directly after an opening section tag and one directly before a closing tag
are marker placement rather than content, and one trailing newline is
removed from each rendered section, so the layout owns boundary whitespace.
[SPB renderer][renderer] [SPB manifest][manifest]

## Acceptance checks

1. Parse a copy of `../symbolic-tools/SYSTEM.md` and recover all eight section
   values in order without changing the Markdown, code fences, or Prolog goals.
2. Render section-level Mustache variables and loops once; a layout receives
   the rendered section strings under `sections.*`, while `tools` still names
   the tool list.
3. Preserve blank lines, Unicode punctuation, and `&`; reject an XML-looking snippet inside a code
   fence with an actionable error rather than silently losing it.
4. Reject duplicate or mismatched section tags, missing closers, parser errors,
   and out-of-section content with a source location.
5. Validate and render through the existing CLI; manifest source and rendered
   hashes change according to their existing definitions. [SPB CLI][cli]
   [SPB manifest][manifest]

## Verification results

All eight sections of `../symbolic-tools/SYSTEM.md` extract in source order,
and each extracted value is byte-identical to the text between its markers.
Empty layouts, duplicate slots, missing slots, and every rejection case in
`tests/test_sections.py` and `tests/test_rendering.py` fail with the intended
diagnostics.

[reference-prompt]: ../../../symbolic-tools/SYSTEM.md
[readme]: https://github.com/mitsuhiko/sloppy-xml-py/blob/main/README.md
[parser]: https://github.com/mitsuhiko/sloppy-xml-py/blob/main/sloppy_xml.py
[package]: https://github.com/mitsuhiko/sloppy-xml-py/blob/main/pyproject.toml
[renderer]: ../../src/spb/rendering.py
[manifest]: ../../src/spb/cli.py
[cli]: ../../src/spb/cli.py
[mustache]: https://github.com/mustache/spec/blob/master/specs/interpolation.yml
