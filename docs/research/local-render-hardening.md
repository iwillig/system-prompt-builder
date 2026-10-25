# Research: local-render hardening

**Date:** 2025-03-08  
**Scope:** repeatable render variables, required-variable validation, local-resolution
error reporting, and safe artifact replacement for System Prompt Builder's next
implementation slice.

## Findings

### Click can represent repeatable `--var` arguments directly

Click's `multiple=True` option collects every occurrence into a tuple. This is
a direct fit for a command such as:

```python
@click.option("--var", "variables", multiple=True, metavar="NAME=VALUE")
```

`spb` should parse each supplied value by splitting on the **first** `=`. This
preserves values containing `=` (for example, a URL query string or encoded
value) while rejecting an empty name and an argument that contains no `=`.
Duplicate names should be rejected rather than silently accepting the last
one: an accidental duplicate otherwise changes a prompt invisibly.

**Source:** [Click options documentation — Multiple Options](https://click.palletsprojects.com/en/stable/options/#multiple-options).

### Mustache itself cannot distinguish an intentionally empty value from a missing one

The official Mustache interpolation specification requires failed lookups to
render as an empty string. It also specifies that `null` interpolates as an
empty string. Therefore, inspecting rendered output cannot reliably identify a
missing variable.

Chevron exposes `warn=True`, which writes a warning to stderr for a failed
lookup, but that is also unsuitable as the core contract: it is an
implementation-specific side effect, and Mustache sections commonly rely on
falsey/missing values for optional content.

The prompt format should instead declare its variable contract explicitly in
front matter. The renderer can then fail only when a **declared required**
variable lacks a supplied value. Optional Mustache values retain normal
Mustache semantics.

**Sources:**

- [Mustache specification — interpolation, null values, and failed context lookups](https://github.com/mustache/spec/blob/master/specs/interpolation.yml)
- [Chevron renderer source — `warn` parameter and empty-string fallback](https://github.com/noahmorrison/chevron/blob/master/chevron/renderer.py)

### Plain `{{name}}` HTML-escapes values

Mustache's specification requires normal interpolation to HTML-escape content;
triple braces and ampersand interpolation do not escape. System prompts are
plain text, so examples and tests should use `{{{project_name}}}` when the
value must remain byte-for-byte unchanged. This behavior should be documented
rather than overridden globally, retaining standard Mustache behavior.

**Source:** [Mustache specification — HTML Escaping, Triple Mustache, and Ampersand](https://github.com/mustache/spec/blob/master/specs/interpolation.yml).

## Current-code validation

The checked implementation confirms the planned work is needed:

| Requirement | Current state | Gap |
| --- | --- | --- |
| Supply render variables | `render_prompt` accepts a `variables` mapping | The CLI exposes no `--var` option. |
| Detect required variables | Chevron receives variables directly | No front-matter declaration or pre-render validation exists; a missing lookup becomes empty text. |
| Validate local references | `render_prompt` resolves provider, skill path, and harness | Errors are surfaced, but tests cover only semantic versions. |
| Prevent accidental artifact replacement | `render` always writes the output and manifest | No comparison with a prior manifest or explicit replacement flag exists. |
| Reproducible manifest | Name/version and source/rendered digests are written | Resolved skills, variable names, and overwrite decision are absent. |

## Decision supported by the research

Use an explicit front-matter variable contract and a repeatable
`--var NAME=VALUE` CLI option. Do not infer required variables by scanning
Mustache tags or depend on Chevron's warning stream. Compare the prior
manifest's prompt identity and rendered digest before replacing an artifact;
require an explicit `--replace-release` flag for a different digest at the
same prompt name/version/harness identity.
