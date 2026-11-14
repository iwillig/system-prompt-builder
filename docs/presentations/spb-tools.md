---
title: "System Prompt Builder"
subtitle: "The spb command-line tools"
author: Ivan Willig
date: 2026-11-03
header-includes: |
  <style>
    /* Slidy's fixed bottom toolbar paints over long slides; hide it.
       Navigation stays on the keyboard: space/arrows, "c" for contents. */
    div.toolbar {
      display: none !important;
    }
  </style>
---

# What spb is

`spb` composes reproducible, versioned system prompts from reusable
Markdown fragments, skills, template variables, and harness-specific
tool metadata.

Prompts are treated like software releases:

- Composed from reusable parts under `.spb/`
- Versioned with author-managed semantic versions
- Rendered deterministically, with provenance manifests
- Evaluated and benchmarked before shipping

Every capability is exposed as a CLI command. This deck walks through
each one.

# Table of contents: the commands

Project lifecycle:

1. `spb init` — scaffold a new prompt project
2. `spb validate` — check project configuration
3. `spb render` — compose a prompt release for a harness
4. `spb link` — install a rendered prompt into a harness

Evaluation:

5. `spb eval validate` — check a suite without model calls
6. `spb eval run` — generate and score responses
7. `spb eval compare` — full prompt vs. compressed variant
8. `spb eval ablate` — measure one fragment's impact

Benchmarking:

9. `spb benchmark run` — gate one release on scores
10. `spb benchmark compare` — compare two prompt versions

# spb init

Scaffolds a prompt project in the current repository.

```bash
spb init [DIRECTORY] [--harness HARNESS]
```

Creates:

- `.spb/config.yaml` — project identity, harnesses, tool metadata
- `.spb/prompts/project-assistant.md` — starter versioned prompt
- `.spb/layouts/` — layout that places fragments in the final text
- `.spb/fragments/` — a reusable instruction fragment
- `.spb/skills/local/` and `.spb/evals/`

It refuses to overwrite any managed starter path, so re-running it is
safe.

# spb validate

Checks the whole project without producing output.

```bash
spb validate [--project-root DIR]
```

Validates:

- `.spb/config.yaml` structure, harnesses, and tool JSON Schemas
- Prompt front matter: name, semantic version, fragments, layout,
  declared variables
- That selected fragments and layouts exist and resolve

Run it in CI before any render or evaluation step.

# Example: .spb/config.yaml

The project file that `validate` checks. It names the project, the
supported harnesses, and each harness's tools with JSON Schemas —
this is how rendered prompts can truthfully list the agent's tools:

```yaml
version: 1
project_name: system_prompt_builder
support_harness:
  - pi_agent
tool_provider_metadata:
  pi_agent:
    tools:
      - name: read
        summary: Read a file, optionally selecting a line range.
        parameters:
          type: object
          properties:
            path:
              type: string
              description: File path.
            offset:
              anyOf: [{type: integer}, {type: "null"}]
              description: First line to read, starting at 1.
          required: [path]
          additionalProperties: false
      - name: write
        summary: Create a file or replace its complete contents.
        # ... parameters schema ...
```

The same tool schemas power mock tools in evaluation suites.

# spb render

Composes a prompt release for one harness.

```bash
spb render PROMPT --harness HARNESS [--var NAME=VALUE]
    [--compress] [--compressor llmlingua] [--rate 0.5]
    [--replace-release]
```

- Renders fragments, layout, skills, variables, and harness tool
  metadata in deterministic order
- Writes `build/HARNESS/NAME.md` plus a manifest with source and
  output hashes, resolved skill hashes, pinned Git revisions, harness
  identity, and non-secret variable values
- Rejects a changed release for an existing name, version, and
  harness unless `--replace-release` is passed
- `--compress` additionally writes an LLMLingua-compressed artifact;
  only fragments listed under `compressible_fragments` are compressed

# Example: prompt front matter and layout

What `render` composes. This repository's own Python assistant —
YAML front matter selects fragments; the layout places them:

```yaml
---
name: Python coding assistant
version: 0.1.9
rationale: Ground codebase answers in evidence, follow PEP 8
  for Python code, and verify edits with project checks.
layout: .spb/layouts/python-assistant.md
skills: []
compressible_fragments: [routing]
fragments:
  identity: .spb/fragments/identity
  tools: .spb/fragments/tools
  rules: .spb/fragments/rules
  python_style: .spb/fragments/python_style
  routing: .spb/fragments/routing
  # ... eleven fragments in total ...
---
```

The layout is Mustache over the fragment aliases:

```markdown
<identity>
{{{fragments.identity}}}
</identity>

<rules>
{{{fragments.rules}}}
</rules>

<python_style>
{{{fragments.python_style}}}
</python_style>
```

`compressible_fragments` is what makes `routing` eligible for
`--compress`, `eval compare`, and `eval ablate --mode rate`.

# spb link

Installs a rendered prompt where the harness reads it.

```bash
spb link SOURCE DESTINATION [--replace]
```

Example:

```bash
spb link build/pi_agent/project-assistant.md .pi/SYSTEM.md
```

The harness (for example Pi) then reads the prompt from its own
location. `--replace` is required to overwrite an existing
destination.

# spb eval validate

Checks an evaluation suite with no model calls.

```bash
spb eval validate .spb/evals/coder.yaml
```

A suite declares:

- `model` — the `llm` model that generates responses
- `judge_model` — independent grader, required for judge metrics
- `metrics` — `answer_relevancy`, `g_eval`, or deterministic
  `code_lint`
- `tests` — named cases with an `input`, optional `group`,
  `expected_output`, `mock_tools`, and `expected_tool_calls`

Catches structural errors before any endpoint cost.

# Example: an evaluation suite

This repository's `.spb/evals/python-style.yaml` — a judge-free suite
that lints generated Python deterministically with Ruff:

```yaml
model: spb-local-qwen
metrics:
  - type: code_lint
    language: python
tests:
  - name: writes a normalized-name function
    group: python-style
    input: >-
      Write a Python function called normalize_name that accepts
      a string, strips leading and trailing whitespace, and
      returns it in lowercase. Return only one fenced Python
      code block tagged python.
  - name: formats a long function signature and validation
    group: layout
    input: >-
      Write a Python function called create_user that accepts
      username, email_address, display_name, and is_active. ...
```

A judge-based suite adds `judge_model` and judge metrics, and a case
can mock tools and assert the exact call trace:

```yaml
judge_model: independent-judge
metrics:
  - type: g_eval
    name: Coding quality
    criteria: Identifies concrete bugs and explains their impact.
    evaluation_steps:
      - Check whether the answer names a concrete bug.
      - Check whether the answer explains the bug's impact.
    threshold: 0.7
tests:
  - name: reads the requested file
    input: Inspect src/example.py and explain count_records.
    mock_tools:
      read: "def count_records(records): return len(records)"
    expected_tool_calls:
      - name: read
        arguments:
          path: src/example.py
    expected_output: It returns the number of records.
```

# spb eval run

Generates responses with the rendered prompt and scores them.

```bash
spb eval run PROMPT --harness HARNESS --suite SUITE
    [--fail-under 0.75] [--dry-run] [--output FILE]
```

- Sends each case's input with the rendered prompt as the system
  prompt — one user turn
- Judge metrics are scored with DeepEval through the suite's
  `judge_model`; `code_lint` is scored deterministically with Ruff
- Mock tools return fixed strings; `expected_tool_calls` asserts the
  exact ordered call trace
- The artifact records prompt and suite digests, model identity,
  outputs, tool traces, metric scores and reasons, and the mean score
- `--fail-under` turns the mean score into a CI gate; `--dry-run`
  checks wiring without model calls

# spb eval compare

Compares the full prompt against a compressed variant on one suite.

```bash
spb eval compare PROMPT --harness HARNESS --suite SUITE
    --compressor llmlingua [--rate 0.5]
    [--max-score-drop 0.05]
```

- Runs the same suite against both versions
- `--max-score-drop` allows a small mean-score drop for judge noise
  before the gate fails
- Only aliases listed under the prompt's `compressible_fragments`
  are compressed; the comparison fails without that front matter key
- `--compressor none` exercises the workflow without loading a
  compression model

# spb eval ablate

Answers one question: **does this fragment earn its place in the
prompt?**

```bash
spb eval ablate PROMPT --harness HARNESS --suite SUITE
    --mode drop|rate|both [--fragments routing]
    [--rates 0.5,0.3,0.1] [--repeats 3] [--noise-floor 0.1]
    [--max-case-generations N] [--dry-run] [--output FILE]
```

It re-renders the prompt with exactly one fragment changed, runs the
same suite against the baseline and each variant several times, and
compares the score distributions.

Three phases, covered on the next slides:

1. **Plan** — build every variant before any model call
2. **Run** — baseline and variants, `--repeats` times each
3. **Aggregate** — classify each case/metric pair and issue a verdict

# eval ablate: planning the variants

Variants are built up front, so a bad plan fails before any cost:

- **`--mode drop`** — one variant per fragment alias; that fragment's
  rendered text becomes the empty string
- **`--mode rate`** — one variant per alias × rate; the fragment is
  LLMLingua-compressed so the rate is the fraction of *its* tokens to
  keep. Only aliases listed under `compressible_fragments` qualify
- **`--mode both`** — the union

Everything else — the other fragments, the layout, skills,
variables — stays byte-identical, so exactly one thing differs from
the baseline.

The planned cost is:

```text
case_generations = (1 + variants) × repeats × cases
```

Example: the project suite has 17 cases. One drop plus two rates is
3 variants, so with 3 repeats:

```text
(1 + 3) × 3 × 17 = 204 case generations
```

`--max-case-generations 204` rejects any larger plan before a single
model call; `--dry-run` stops after printing the plan.

# eval ablate: the aggregation expressions

Why repeats? A single judge score is noise — it cannot distinguish
"the fragment mattered" from "the judge wavered."

With `n` repeats, each `(case, metric)` pair has `n` baseline and `n`
variant results. Let `bp` and `vp` be the pass counts. The rules,
checked in order:

```text
bp == n  and  n - vp > n/2     →  REGRESSION evidence
bp == 0                        →  "baseline never passed"   (reason)
bp != n                        →  "baseline mixed"          (reason)
vp != n                        →  "variant mixed"           (reason)
median(baseline_scores)
  - median(variant_scores)
  > noise_floor                →  "material score decrease" (reason)
```

The first line is the only regression trigger: the baseline passed in
**all** repeats and the variant failed in a **majority**. With
`n = 3`: baseline 3/3 passed, variant at most 1/3 passed.

Worked score example, `noise_floor = 0.1` (the default):

```text
baseline scores:  0.82, 0.85, 0.80   → median 0.82
variant scores:   0.70, 0.73, 0.68   → median 0.70
0.82 − 0.70 = 0.12 > 0.1             → material score decrease
```

Both sides still pass their threshold here, so this is a *reason*,
not a regression — but it blocks a clean verdict.

Tool-call traces get the same majority rule per case: baseline trace
passed `n/n` while the variant failed a majority → regression
evidence; anything mixed becomes a reason.

# eval ablate: verdicts and the report

Each variant receives exactly one verdict:

```text
any regression evidence        →  REGRESSION
else any reason, or n < 3,
  or no scored metrics         →  INDETERMINATE
else                           →  NO_REGRESSION_DETECTED
```

- Runs with fewer than three repeats are flagged `exploratory` and
  can never reach `NO_REGRESSION_DETECTED`
- `REGRESSION` means an observed majority failure against a *stable*
  baseline; an unstable baseline can only yield `INDETERMINATE`
- `NO_REGRESSION_DETECTED` is scoped to the evaluated suite — it
  means "these cases caught no difference," not "the fragment is
  universally redundant"

The YAML report keeps all the evidence, not just the verdict:

- `baseline_runs` and per-variant `runs` — every raw score, output,
  and judge reason
- Per-metric spreads: all repeat scores, medians, min/max, pass
  counts on both sides
- `traces` — expected and actual tool calls per repeat
- `matrix` — one `variant × case × metric → median_delta` row for
  quick scanning

Findings are reported without a CI failure gate — read the verdicts
alongside `reasons` and the raw runs before acting on them.

# spb benchmark run

Gates one prompt release on overall and per-group scores.

```bash
spb benchmark run PROMPT --harness HARNESS --suite SUITE
    [--fail-under 0.75] [--min-group-score safety=0.9]
```

- Cases carry an optional `group` label (default `default`)
- `--fail-under` gates the overall mean score
- `--min-group-score NAME=SCORE` gates a named group, so a safety
  group can be held to a stricter bar than the rest

# spb benchmark compare

Compares two prompt source versions on the same suite.

```bash
spb benchmark compare BASELINE CANDIDATE
    --harness HARNESS --suite SUITE
    [--max-score-drop 0.02]
    [--max-group-score-drop safety=0.01]
```

- Both prompts use the same harness, variables, and suite
- Records overall and per-group score drops
- `--max-score-drop` and `--max-group-score-drop` turn those drops
  into gates, so a release cannot silently regress a group

# A typical workflow

```bash
spb init                               # scaffold the project
spb validate                           # check configuration
spb render .spb/prompts/coder.md \
    --harness pi_agent                 # compose a release
spb eval validate .spb/evals/coder.yaml
spb eval run .spb/prompts/coder.md \
    --harness pi_agent \
    --suite .spb/evals/coder.yaml \
    --fail-under 0.75                  # score the release
spb eval ablate ... --dry-run          # preview fragment cuts
spb benchmark compare old.md new.md \
    --harness pi_agent --suite ...     # gate the upgrade
spb link build/pi_agent/coder.md \
    .pi/SYSTEM.md                      # ship it
```

# Boundaries and pointers

What evaluation does **not** do:

- No real harness tools run — mock tools return fixed strings
- One user turn only — no multi-turn conversations or full agent
  trajectories

Where to read more:

- Documentation: <https://www.iwillig.me/system-prompt-builder/>
- CLI reference, prompt authoring, and the evaluation guide cover
  every option shown here
