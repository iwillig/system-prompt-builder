# Plan: local-render hardening

**Status:** proposed  
**Research:** [`../research/local-render-hardening.md`](../research/local-render-hardening.md)  
**Goal:** complete the local-render MVP by making render inputs explicit,
fail-fast, reproducible, and resistant to accidental release replacement.

## Scope

This plan implements the next four local-only capabilities:

1. Repeatable `--var NAME=VALUE` input for `spb render`.
2. Explicit prompt-front-matter variable declarations and required-variable
   validation.
3. Clear validation failures for local providers, skills, and harnesses.
4. Artifact collision protection based on the existing manifest's identity and
   rendered digest.

It does **not** add Git providers, compression, Promptfoo export, symlinks, or
variable substitution inside imported skills. Those remain later milestones.

## User-facing design

### Prompt variable contract

Prompt front matter gains an optional `variables` mapping:

```markdown
---
name: TypeScript coder
version: 1.1.0
skills:
  - local/code-review
variables:
  project_name:
    required: true
  response_style:
    default: concise
---

You are assisting {{project_name}}. Keep responses {{response_style}}.
```

Rules:

- Every declared variable name must match `[A-Za-z_][A-Za-z0-9_]*`.
- A declaration contains exactly one of `required: true` or `default: <value>`.
- CLI values override defaults.
- A render fails before Mustache rendering when a required declaration has no
  CLI value.
- User variables may not be named `harness` or `tools`; those are reserved
  renderer-provided contexts.
- Undeclared Mustache values retain normal Mustache behavior. This is
  intentional: Mustache specifies that unresolved values become empty strings,
  so `spb` can only reliably fail on its explicit variable contract without
  imposing a nonstandard template language.
- Prompt authors should use triple-Mustache form (`{{{project_name}}}`) for
  values that must not be HTML escaped. Normal `{{project_name}}` remains
  standard Mustache interpolation.

### CLI

```bash
spb render prompts/typescript-coder.md \
  --harness pi-agent \
  --var project_name=acme \
  --var response_style=direct
```

`--var` is repeatable. The parser splits at the first `=` only, so values may
contain `=`. It rejects a missing separator, an empty name, invalid names,
duplicate names, and reserved names.

### Artifact replacement policy

Before replacing `build/<harness>/<prompt-stem>.md`, `spb` reads its paired
manifest when it exists:

- Same `name`, `version`, `harness`, and `rendered_sha256`: allow the idempotent
  rewrite.
- Same `name`, `version`, and `harness`, but a different digest: fail with a
  release-collision error.
- Existing output without a readable `spb` manifest: fail safely.
- `--replace-release` is required to replace either collision case. The command
  must print a warning naming the replaced identity and prior/new digests.

The flag is deliberately explicit because a prompt's semantic release version
is intended to identify an evaluated behavior. Normal content changes require a
version bump rather than silent replacement.

### Manifest additions

Keep existing fields and add:

```yaml
variables:
  project_name: acme
  response_style: direct
skills:
  - reference: local/code-review
    path: skills/local/code-review.md
    sha256: "..."
```

Variables with names matching `password`, `secret`, `token`, or `key`
(case-insensitive) must be omitted and listed only by name under
`redacted_variables`. This conservative first policy avoids placing obvious
credential values in generated artifacts.

## Implementation steps

### 1. Add focused test fixtures

Extract the duplicated temporary project setup in `tests/test_cli.py` into a
small fixture helper. Preserve the agreed seams:

- CLI tests use `click.testing.CliRunner`.
- Rendering tests call public `render_prompt(...)`.

No tests should call private helpers directly.

### 2. Implement the variable contract in the rendering API

Add a public, immutable variable-contract/result type if needed, then:

1. Parse and validate `variables` front matter.
2. Merge defaults, then CLI variables, without allowing built-in context
   replacement.
3. Fail on missing required declarations before calling Chevron.
4. Pass the resolved values to `chevron.render`.
5. Retain the resolved non-secret values and skill provenance in
   `RenderedPrompt` so the CLI does not reconstruct rendering facts.

This keeps prompt composition as the single source of truth and lets both CLI
and future Promptfoo export use the same result.

### 3. Add CLI parsing

Add `@click.option("--var", "variable_pairs", multiple=True,
metavar="NAME=VALUE")` to `render`. Convert the tuple to a mapping in a
small, independently tested public-or-module-boundary parser. Pass the mapping
to `render_prompt`.

Do not add `--var` to `validate`: validation has no user-specific render input.
`validate` should instead report a prompt's required variables as an unmet
runtime requirement only if it needs to compose a prompt; refactor validation
to validate static structure without attempting a concrete render.

### 4. Preserve richer provenance

Refactor local skill resolution to return a small resolved-skill value
(reference, path, content, SHA-256). Build the render result from those values,
and serialize their public provenance into the manifest. Add resolved variables
and redaction information.

### 5. Gate artifact writes

Create an artifact-writing boundary responsible for:

1. Computing output and manifest paths.
2. Loading and validating a previous manifest, if present.
3. Applying the collision policy.
4. Writing prompt and manifest only after the policy allows it.

Write both files via temporary sibling files and `Path.replace()` so a process
interruption does not leave a partially written artifact pair. The plan does
not attempt cross-process locking; that can be added if concurrent build
writers become a supported workflow.

### 6. Update documentation

Update `readme.md` with the variable contract, repeated `--var` examples,
Mustache escaping guidance, manifest fields, redaction behavior, and
`--replace-release` policy.

## TDD sequence and acceptance tests

Implement each row as a red → green vertical slice.

| Slice | Public seam | Required test |
| --- | --- | --- |
| CLI values | `spb render` | Two `--var` values render correctly; a value containing `=` is preserved. |
| CLI errors | `spb render` | Missing `=`, empty/invalid/duplicate/reserved names fail with an actionable error. |
| Required contract | `render_prompt` | Missing required variable fails before output; CLI value overrides a default. |
| Static validation | `spb validate` | Invalid variable declaration fails without requiring runtime variables. |
| Local-resolution errors | CLI and API | Unknown harness, unknown provider, and missing skill identify the failing reference/path. |
| Provenance | `spb render` | Manifest contains resolved non-secret variables and skill path/digest; secret-like values are redacted. |
| Idempotency | `spb render` | Re-rendering identical input succeeds. |
| Collision safety | `spb render` | Same name/version/harness with a changed digest fails; `--replace-release` succeeds and warns. |
| Legacy safety | `spb render` | An output lacking a readable manifest fails unless explicitly replaced. |

All existing tests remain green. Each slice must also pass:

```bash
pipenv run test
pipenv run lint
pipenv run format-check
pipenv run typecheck
```

## Research validation and design constraints

The plan was checked against the current code and primary-source behavior:

- Click natively supports a repeatable option as a tuple, validating the
  `multiple=True` CLI design.
- Mustache deliberately renders unresolved values as empty strings; an explicit
  front-matter contract is necessary for dependable required-variable errors.
- Chevron's `warn=True` only writes warnings to stderr and is not used as an
  error mechanism.
- Current `render_prompt` already accepts a variable mapping, making the
  rendering API the natural merge/validation boundary.
- Current `render` overwrites artifacts without comparison, so manifest gating
  is required to honor the documented prompt-version policy.

See the linked research note for sources and the detailed current-code gap
analysis.

## Completion criteria

This plan is complete when a local project can safely render a versioned prompt
with declared variables, produce a redacted provenance manifest, reject an
accidental changed release, and intentionally replace one only through the
explicit override flag.
