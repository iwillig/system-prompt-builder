# Plan: compose system prompts from fragments and export skills

**Status:** fragment composition implemented; skill export and skill ingestion not implemented.  
**Research:** [Prompt fragments, compositions, and skills](../research/prompt-fragments-and-composition.md).  
**Domain language:** [System Prompt Builder glossary](../../CONTEXT.md).

## Outcome

Give system prompts first-class identity and explicit ownership of their inputs. A system prompt selects named, reusable fragments; its separate layout places the rendered fragment values into the final text. Fragments never include fragments. Exporting a fragment as a skill produces a real `SKILL.md` package with discovery metadata, not appended system-prompt text. Preserve provenance and the existing render/evaluation entry points. [Domain language](../../CONTEXT.md) [Current rendering](../../src/spb/rendering.py) [Agent Skills specification](https://agentskills.io/specification)

The fragment binding and layout syntax below are implemented. Skill export syntax remains proposed.

## Proposed authoring contract

A fragment is an instruction bundle under `.spb/fragments/<id>/`, with `FRAGMENT.md` as its text and optional resource files kept at their original relative paths. For prompt use today, a bundle may contain only `FRAGMENT.md` and an optional `fragment.yaml` specifying its mode. For example, `.spb/fragments/identity/FRAGMENT.md` needs no resources; an imported skill can also retain `scripts/`, `references/`, and `assets/`. Fragment instructions never include other fragments. Record an explicit rendering mode: authored template fragments use Mustache, while imported skills are literal so examples such as `{{name}}` remain unchanged. A system prompt stays under `.spb/prompts/` and owns its identity, version, variable declarations, layout choice, and alias-to-fragment bindings. In this first slice, a selected fragment must be self-contained for prompt use: if it was imported with bundled resources or has unresolved resource dependencies, rendering fails until an author explicitly adapts it for prompt use. Import and skill re-export still preserve its full bundle. [Skill ingestion plan](skill-ingestion.md)

Proposed definition:

```yaml
---
name: Python coding assistant
version: 0.2.0
layout: .spb/layouts/python-assistant.md
fragments:
  identity: .spb/fragments/identity
  tools: .spb/fragments/tools
  rules: .spb/fragments/rules
variables:
  project_name:
    required: true
---
```

Its layout remains a Markdown template and owns the surrounding markup and placement:

```mustache
<identity>
{{{fragments.identity}}}
</identity>

<rules>
{{{fragments.rules}}}
</rules>

<tools>
{{{fragments.tools}}}
</tools>
```

Bindings belong to the system prompt, not the layout. The same fragment can have different aliases in two prompts; a layout can insert a selected alias in more than one place when repetition is intentional. The layout cannot reach arbitrary files or select undeclared fragments. Each declared alias must appear at least once, and every `fragments.*` lookup must resolve; duplicate insertion is allowed. Triple braces preserve plain Markdown. Render template-mode fragments with harness/tool/variable context and leave literal-mode fragments untouched; then render the layout with only the resulting `fragments` mapping. Keep the existing newline-boundary behavior and pin it with exact-output tests. [Current two-pass rendering](../../src/spb/rendering.py) [Mustache interpolation](https://github.com/mustache/spec/blob/master/specs/interpolation.yml)

A separate export definition gives a skill its own identity and discovery description:

```yaml
# .spb/skill-exports/code-review.yaml
name: code-review
description: Review code changes when asked for a review.
fragment: .spb/fragments/code-review
```

Proposed command: `spb skill export .spb/skill-exports/code-review.yaml`. The output is `build/skills/code-review/SKILL.md` with skill front matter and the fragment instructions as its body, and copies the bundle's resources without changing their relative paths or bytes. A sidecar manifest outside the skill directory records hashes for the definition, body, and every resource. Imported skill bodies are literal text, so a `{{...}}` example must survive re-export unchanged. For authored templated fragments, either require a fully resolved export context or reject export; never silently interpolate examples or publish unresolved required inputs. Importing an existing skill into this fragment bundle is a separate follow-up plan, but export must preserve such bundles from the start to support round trips. Neither export nor import implies a runtime loader. [Agent Skills specification](https://agentskills.io/specification) [Skill ingestion plan](skill-ingestion.md)

## Implementation sequence

1. **Contract tests before refactoring.** Add public `render_prompt` and CLI tests for two system prompts sharing a fragment, alias placement into different layout sections, repeated placement, unknown and unused aliases, missing files, traversal/symlinks outside `.spb/fragments/`, invalid prompt metadata, and byte-exact whitespace. Test that fragment files cannot resolve another fragment and that resource-dependent bundles fail prompt rendering until adapted. Establish the output of the current `.spb/prompts/python-assistant.md` as a fixture before migrating it. [Rendering tests](../../tests/test_rendering.py) [CLI tests](../../tests/test_cli.py)
2. **Introduce a fragment reader and composition result.** Parse the system prompt definition, validate identity/version/variables, resolve aliased bundles under the fragments root, apply each fragment's explicit literal or template mode once per alias, and hand the resulting mapping to the layout renderer. Keep file I/O and template rendering behind the existing `render_prompt(project_root, prompt_path, *, harness, variables)` interface so eval and benchmark commands continue to work. Model selected fragment provenance (alias, path, digest) on the render result rather than recreating it in the CLI. [Renderer](../../src/spb/rendering.py) [Evaluation calls](../../src/spb/cli.py)
3. **Make static validation and output provenance honest.** Have `spb validate` inspect every prompt and its referenced fragments/layout without requiring runtime variable values. Detect unknown layout references instead of letting Mustache render them as empty text. Record each fragment's source digest alongside the prompt, layout, harness, variable, and output digests. Retain release-collision behavior for changes to any contributing fragment. [Validation](../../src/spb/rendering.py) [Manifest and release guard](../../src/spb/cli.py)
4. **Export a real skill package.** Add the export definition reader and a CLI command. Validate skill metadata against the Agent Skills contract. Build a complete skill directory in a temporary location, copying every bundled resource with safe relative paths and rejecting symlinks/path escapes; publish it only after all checks pass. Record definition, fragment, and resource hashes in a sidecar manifest. Test the generated directory with the published `skills-ref` validator if available, and assert its contents independently in pytest. Never append the exported skill to system prompt output. [Agent Skills specification](https://agentskills.io/specification) [Current skill append](../../src/spb/rendering.py)
5. **Migrate examples and retire obsolete structure.** The repository's two prompts and `spb init` now use fragment bundles and separate layouts, with byte-identical starter output. Prompt authoring, initialization, CLI, and README documentation describe fragments. A future release note can record this change. Explicitly choose what to do with existing `skills:` provider references: they still append Markdown and are not skill-package exports. Do not silently reinterpret them. Remove the unused pseudo-XML section parser and its dependency only if nothing else needs the legacy inline-section format. [Current example](../../.spb/prompts/python-assistant.md) [Current layout](../../.spb/layouts/python-assistant.md) [Initializer](../../src/spb/initialization.py) [Section parser](../../src/spb/sections.py)

## Scope and trade-offs

- **No recursive includes.** Only a system prompt binds fragment aliases; fragment content cannot reference another fragment. This keeps ordering, diagnostics, and provenance flat. [Domain language](../../CONTEXT.md)
- **The layout still exists.** It controls wrappers, order, and repetition, but selecting fragments is the system prompt's responsibility. This retains flexible placement at the cost of looking at two files to understand a composition.
- **Skill export is separate from prompt rendering.** A skill may bundle resources; exporting copies those resources, but prompt rendering rejects an imported resource-dependent fragment until an author makes a deliberate prompt-safe adaptation. Treat imported text as literal by default to preserve examples that resemble Mustache syntax. This avoids silently producing instructions with broken relative paths. The ingestion workflow and any future automated adaptation are scoped in the [separate ingestion plan](skill-ingestion.md). [Agent Skills specification](https://agentskills.io/specification)
- **Source compatibility is a migration choice.** Existing sectioned prompt files and `skills:` references are currently valid; removal changes authoring behavior. Keep the old reader temporarily during the example migration, then either provide an explicit conversion command or document the required edits before removal. Do not infer public adoption from the repository's present examples. [Current format](../prompts.rst)

## Acceptance and verification

- Two prompts select one shared fragment and place it in different layout sections; repeated use in one layout is deterministic. A fragment cannot compose or render another fragment.
- Invalid aliases, missing/escaped fragment paths, unresolved layout slots, and skill metadata fail validation with actionable file locations. Static validation needs no runtime variable values.
- Migrated Python assistant output is byte-identical before and after migration for the same harness and bindings; fragment edits change the rendered hash and trigger the existing release-collision guard unless explicitly replaced.
- Exported `SKILL.md` has valid `name` and `description` front matter, the expected instruction body, and any bundled resources with byte-identical relative contents. It is not included in the system-prompt artifact. A resource-dependent fragment cannot render into a prompt until explicitly adapted. No claim about dynamic agent loading is made without a harness integration test.
- Focused tests pass, then `just check`, `just docs`, and `just package-check` pass for the eventual implementation. This plan itself does not run live model evaluation.

## Decisions needed before coding

1. Should existing `skills:` provider references remain as a separate legacy *embed* feature, or be removed when skill export lands? Export cannot silently preserve their eager-append semantics.
2. Should skill exports allow template variables? Bundled resources are in scope, but interpolating instructions or resource files needs an explicit contract and is deferred.
