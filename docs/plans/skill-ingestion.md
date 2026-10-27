# Plan: ingest existing skills as fragments

**Status:** proposed, not implemented.  
**Prerequisite:** [Fragment composition and skill export](fragment-composition-and-skill-export.md).  
**Research:** [Prompt fragments, compositions, and skills](../research/prompt-fragments-and-composition.md); [Agent Skills specification](https://agentskills.io/specification).

## Outcome

Import an existing Agent Skills directory as a complete SPB fragment bundle, then allow the bundle to be re-exported as a valid skill without losing its instructions, metadata, or bundled files. A skill with resource dependencies is not automatically prompt-safe: it cannot be placed into a system prompt until an author explicitly creates an adapted fragment. Optional LLM-assisted translation is a separate later task; the initial importer is deterministic and makes no model calls. [Agent Skills specification](https://agentskills.io/specification) [Domain language](../../CONTEXT.md)

This plan describes proposed commands and files; SPB does not implement import or bundle export today. The current skill provider reads a Markdown file and appends its text during prompt rendering. [Current renderer](../../src/spb/rendering.py)

## Proposed import contract

```console
spb skill import path/to/code-review --project-root .
```

The source is a directory containing `SKILL.md`, not a Markdown file alone. The importer produces:

```text
.spb/fragments/code-review/
  FRAGMENT.md              # SKILL.md instruction body, preserved as literal text
  scripts/                 # copied with the original relative paths
  references/
  assets/
  ...                      # any other regular bundled files
.spb/skill-exports/code-review.yaml
```

The export definition retains the parsed front matter, including required `name` and `description` and any optional metadata, and points to the fragment directory. Mark the imported fragment as `literal` rather than `template`; otherwise Mustache-shaped examples in the original instructions could change during later rendering. Keep unknown metadata fields as data when they can be safely represented; reject ambiguous YAML or metadata that cannot be preserved, rather than discard it. The fragment bundle also records its origin and a per-file digest inventory in SPB provenance outside the skill artifact. The skill's original `SKILL.md` is split into front matter and body without template evaluation or prose rewriting. The import must not infer that an imported skill is now a system prompt, nor add its instructions to a prompt automatically. [Agent Skills specification](https://agentskills.io/specification)

An imported fragment with any bundled resources is marked **not prompt-compatible**. Its bundle remains available for faithful skill re-export. To use its ideas in a system prompt, an author creates a separate, self-contained fragment with an explicit `derived_from` link to the imported bundle, edits resource-dependent instructions for the prompt environment, and reviews the rendered output. Merely setting a flag on the unmodified imported bundle is not an adaptation. Imported fragments without bundled resources still need explicit review for external paths or runtime assumptions; a static scan cannot prove that instructions are portable. [Domain decision](../research/prompt-fragments-and-composition.md)

## Implementation sequence

1. **Fixture and validator tests.** Prepare a minimal skill, a skill with `scripts/`, `references/`, `assets/` and additional files, a skill with literal Mustache examples, and invalid/hostile directories. Test parsed metadata, exact instruction bytes after the front-matter boundary, relative paths, resource hashes, and expected failures. Use the published `skills-ref` validator where available; do not mistake validation for an audit of executable files. [Agent Skills specification](https://agentskills.io/specification)
2. **Safe deterministic importer.** Validate `SKILL.md` name and description against the skill specification; require the name to match its directory. Read and copy every regular file in the skill directory, preserving bytes and relative paths. Reject symlinks, traversal, special files, duplicate/case-colliding names, oversized bundles, and destination collisions before writing. Stage all outputs and publish only on success. Do not execute scripts or follow links while importing. Record source path and digests for future comparison.
3. **Preserving export.** Make the skill exporter accept imported fragment bundles and the saved metadata without rewriting literal instruction text. Copy all resources under the same relative paths. Check the parsed front-matter values and instruction body, and compare the input and output file inventories byte-for-byte for every resource. Regenerated front-matter formatting need not match byte-for-byte, but its parsed values must match. A changed fragment is an intentional new export, not a claim of an unchanged round trip. [Skill export plan](fragment-composition-and-skill-export.md)
4. **Prompt-use guard and explicit adaptation.** Integrate the renderer guard from the prerequisite plan: importing resource-bearing skills must never turn them into silently renderable prompt fragments. Add a documented authoring path for a separate self-contained fragment that cites its source bundle. Test that a raw imported bundle fails prompt rendering and that an adapted, reviewed fragment can be selected by a system prompt's alias and inserted by its layout. Do not try to rewrite arbitrary relative file references automatically. [Prompt composition plan](fragment-composition-and-skill-export.md)
5. **CLI and documentation.** Document import, re-export, provenance, manual adaptation, and limitations in the CLI and prompt-authoring guides. Include one resource-bearing example and a dry-run or preview that reports files and overwrite conflicts before mutation. Keep Git-provider acquisition separate: first import a local directory, then consider pinned remote sources using the existing provider checkout logic as a later extension. [Current Git provider](../../src/spb/rendering.py)

## Secondary task: assisted translation

Only after the deterministic flow works, explore `spb skill adapt` as an optional **proposal generator**. A small LLM could suggest a self-contained system-prompt fragment from a resource-bearing skill and identify assumptions about tools, paths, and scripts. It must write to a new draft, never modify the imported bundle or automatically declare a fragment prompt-compatible. Require author review, a before/after diff, the source inventory, and explicit confirmation before accepting the draft. Model output must not execute scripts or fetch arbitrary resources; credentials and private skill data must not be sent to a model without an explicit opt-in. Evaluate candidate drafts against fixtures for dropped constraints, invented capabilities, and broken paths before considering automation. No model dependency is required for import or re-export.

## Acceptance and verification

- Import of a resource-bearing skill retains every regular bundled file and relative path, complete supported front-matter values, and the literal instruction body. Existing paths, scripts, and instructions are never executed during import.
- Immediate re-export produces a skill with the same parsed metadata, instruction body, and byte-identical resource inventory; invalid or escaped paths fail without partial output.
- A resource-bearing imported bundle cannot be rendered into a system prompt until a separate prompt-safe adaptation is authored and reviewed. The original remains re-exportable.
- No LLM call occurs in the deterministic import/export path. Optional assisted translation cannot overwrite originals or declare its own output approved.
- Focused importer/exporter and CLI tests pass; implementation work then runs `just check`, `just docs`, and `just package-check`.

## Decisions still needed

- How should import behave when a skill carries unsupported vendor-specific metadata or links outside its directory? Fail closed by default; any exception needs an explicit compatibility contract.
- What size/file-count limit and license review policy should apply to third-party skill bundles? Decide before accepting remote sources or running any bundled code.
