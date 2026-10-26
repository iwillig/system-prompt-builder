# System Prompt Builder

System Prompt Builder (`spb`) composes reproducible LLM system prompts from
project configuration, prompt Markdown, reusable skills, and harness-specific
tool metadata. It produces full-fidelity and optionally compressed prompt
artifacts, and can evaluate them through direct model calls and DeepEval.

## License

Copyright © 2026 Ivan Willig. Licensed under the
[GNU Affero General Public License v3.0 or later](LICENSE).

## Why

Skills and system prompts solve complementary problems. Skills provide focused,
reusable instructions, while a system prompt defines the durable operating
context of an agent: its role, constraints, tools, and priorities.

`spb` makes that composition explicit and versioned. A prompt author writes a
custom introduction, selects skills from configured providers, renders the
result for an agent harness, and can compare uncompressed and compressed
variants through evaluation.

## Concepts

- **Project configuration**: `.spb/config.yaml` declares skill providers and
  supported agent harnesses.
- **Prompt**: a versioned Markdown file with YAML front matter. It supplies
  the prompt's metadata, selected skills, and custom instruction text.
- **Skill**: reusable Markdown instructions supplied by a local directory or a
  pinned Git repository.
- **Provider**: a named source of skills. A provider-qualified reference such
  as `team/code-review` resolves `code-review` through the `team` provider.
- **Harness**: an agent runtime, such as `pi-agent`, whose available tools and
  metadata can be rendered into the prompt.
- **Artifact**: the assembled prompt and manifest emitted by `spb`.

## Project layout

```text
.spb/
  config.yaml
  skills.lock.yaml          # generated when Git providers are resolved
  cache/                    # generated local cache for fetched providers
prompts/
  typescript-coder.md
skills/
  local/
    code-review.md
build/                      # generated artifacts
```

## Configuration

`.spb/config.yaml` is the project-level configuration file.

```yaml
version: 1
project-name: Test System Prompt Project
author: Ivan Willig

support-harness:
  - pi-agent

tool-provider-metadata:
  pi-agent:
    tools:
      - name: read
        summary: Read a file from the project.
      - name: bash
        summary: Execute a shell command in the project.

skill-providers:
  - name: local
    type: local
    path: skills/local

  - name: team
    type: git
    gitrepo: https://example.com/engineering/agent-skills.git
    revision: 0123456789abcdef0123456789abcdef01234567
    skill-root: skills
```

### Skill providers

A provider name is part of every skill reference. `spb` supports these provider
types:

- `local`: reads skills from `path`, relative to `.spb/config.yaml`.
- `git`: clones `gitrepo` into `.spb/cache/` and reads skills below
  `skill-root`.

Git providers must declare an immutable commit SHA in `revision`. When skills
are resolved, `spb` records the exact revision and resolved files in
`.spb/skills.lock.yaml`; this makes a rendered artifact reproducible. Branches
and floating tags are not the default workflow.

A skill is a Markdown file. For v1, `spb` includes its Markdown body in full;
section-level imports are deliberately out of scope.

## Prompt authoring

Prompts are Markdown files with YAML front matter. Markdown with front matter
is the canonical v1 prompt format; standalone YAML prompts are not supported.

```markdown
---
name: TypeScript coder
version: 1.0.0
rationale: A coding-agent prompt for TypeScript work.
skills:
  - local/code-review
  - team/typescript
variables:
  project_name:
    required: true
  response_style:
    default: concise
---

# Introduction

You are a coding agent running in {{harness.name}}.

Use the following tools:

{{#tools}}
- `{{name}}`: {{summary}}
{{/tools}}

Follow the imported skills below.
```

`spb` renders the prompt body with Mustache. The v1 rendering context includes:

- `harness.name`: the selected harness name.
- `tools`: the selected harness's configured tool list.
- Explicit values passed using repeatable `--var key=value` options.

Prompt-authored variables are declared in front matter. A declaration must use
exactly one of `required: true` or `default: <value>`. Required variables must
be supplied to `render`; CLI values override defaults. Variable names use
`[A-Za-z_][A-Za-z0-9_]*`, and `harness` and `tools` are reserved.

```bash
spb render prompts/typescript-coder.md --harness pi-agent \
  --var project_name=acme --var response_style=direct
```

`--var` splits at the first `=`, so values may themselves contain `=`. Duplicate,
invalid, reserved, and undeclared variable names are errors. Missing required
variables and references to unsupported harnesses are also validation errors.

Mustache normally HTML-escapes `{{variable}}`. Use `{{{variable}}}` when a
plain-text prompt value must remain unescaped.
Skills are incorporated in the exact order listed in front matter, after the
prompt body. This ordering is deterministic and is recorded in the artifact
manifest.

## Prompt versioning

Every prompt must declare an author-managed [semantic version](https://semver.org/)
in its front matter:

```yaml
version: 1.0.0
```

The version is a human-facing release identifier for the prompt's intended
behavior. Bump the patch version for corrections that preserve the prompt's
intent, the minor version for backward-compatible instruction or skill changes,
and the major version for changes that materially alter the agent's expected
behavior, role, or harness contract.

A release version alone does not prove exactly what was rendered. Therefore,
each artifact manifest also records:

- the prompt source SHA-256 digest;
- the fully rendered, uncompressed prompt SHA-256 digest;
- the compressed prompt digest when compression is enabled;
- the resolved skill files and their content digests;
- pinned Git provider revisions;
- the selected harness and non-secret render variables.

`spb` rejects an attempt to overwrite an existing artifact with the same prompt
name, version, and different rendered digest unless the caller explicitly
selects an overwrite/release-replacement workflow. Prompt source files should
also remain in Git, which provides the human-readable history behind each
release version.

Use the prompt version and rendered digest together in evaluation results and
release notes. This distinguishes a stable release label (for example,
`typescript-coder@1.2.0`) from the exact evaluated artifact.

## Commands

The initial CLI is designed around an inspectable, uncompressed rendering path.

```bash
# Validate project configuration and prompt references.
spb validate

# Render an uncompressed prompt for one harness.
spb render prompts/typescript-coder.md --harness pi-agent

# Supply Mustache variables while rendering.
spb render prompts/typescript-coder.md --harness pi-agent \
  --var project_name=acme --var response_style=direct
```

Rendering produces artifacts similar to:

```text
build/pi-agent/typescript-coder.md
build/pi-agent/typescript-coder.manifest.yaml
```

The manifest records the prompt name and release version, source prompt,
resolved skills and their content digests, provider revisions, selected harness,
non-secret render variables, output hashes, and compression settings. Variable
values whose names contain `password`, `secret`, `token`, or `key` are omitted
from the manifest and listed under `redacted_variables` instead.

A build may be safely repeated when it produces the same prompt digest. If an
existing artifact has the same prompt name, version, and harness but a different
rendered digest, `spb` rejects it as a release collision. Bump the prompt
version, or explicitly replace it when that is intentional:

```bash
spb render prompts/typescript-coder.md --harness pi-agent \
  --var project_name=acme --replace-release
```

## Compression

Compression is optional and never replaces the normal rendered prompt as the
source of truth:

```bash
spb render prompts/typescript-coder.md --harness pi-agent --compress

# Verify compression plumbing without loading a model.
spb render prompts/typescript-coder.md --harness pi-agent --compress --compressor none
```

This produces both the complete composed prompt and a compressed variant:

```text
build/pi-agent/typescript-coder.md
build/pi-agent/typescript-coder.compressed.md
```

The compressor operates on the complete assembled prompt, so it can optimize
across the custom introduction and imported skills. `none` returns the original
render unchanged and is useful for testing artifact workflows. `llmlingua` is
an optional dependency because it downloads/loads a model; install it only when
needed:

```bash
pipenv run pip install '.[llmlingua]'
```

When compression is enabled, the manifest records the compressor name, settings,
and SHA-256 digest of the compressed artifact.

## Linking compiled output

Projects may keep prompt sources separate from the repository that consumes the
compiled prompt. Linking is explicit rather than an implicit side effect of
rendering:

```bash
spb link build/pi-agent/typescript-coder.md ../consumer/.agent/system.md
```

The command creates an absolute symlink and creates missing destination
parent directories. It refuses to replace an existing file or symlink unless
the replacement is explicit:

```bash
spb link build/pi-agent/typescript-coder.md ../consumer/.agent/system.md --replace
```

CI environments can consume the generated artifact directly instead of relying
on symlinks.

## DeepEval prompt testing

`spb` can run a versioned prompt against direct model calls using Simon
Willison's [`llm`](https://llm.datasette.io/) library, then score each response
with [DeepEval](https://deepeval.com/). Install the optional dependencies:

```bash
pipenv run pip install '.[eval]'
```

### Local llama.cpp model

See [the local llama.cpp runbook](docs/runbooks/local-llama-cpp.md) for setup,
health checks, and evaluation commands.

The repository includes a launcher for the cached
`unsloth/Qwen3.6-35B-A3B-GGUF:Q8_0` model. It starts llama.cpp offline on port
8080 and exposes the OpenAI-compatible API with the `spb-local-qwen` alias:

```bash
./scripts/run-local-llama.sh
```

Configure Simon Willison's `llm` library once on the machine that runs
Evaluations. Add this entry to
`~/.config/io.datasette.llm/extra-openai-models.yaml`:

```yaml
- model_id: spb-local-qwen
  model_name: spb-local-qwen
  api_base: http://localhost:8080/v1
```

Set `model: spb-local-qwen` in a suite to use the local server. Use
`LLAMA_PORT=8081 ./scripts/run-local-llama.sh` to select another port, and
update `api_base` to match.

Create an evaluation suite:

```yaml
# evals/typescript-coder.yaml
model: spb-local-qwen
judge_model: independent-judge
metrics:
  - type: answer_relevancy
    threshold: 0.7
  - type: g_eval
    name: Coding quality
    criteria: Identifies concrete bugs and explains their impact.
    threshold: 0.7
tests:
  - name: reviews a function
    input: Review this function for bugs.
    expected_output: A concrete bug report.
```

Run it against the composed prompt:

```bash
# Validate the suite without credentials or model calls.
spb eval validate evals/typescript-coder.yaml

# Validate prompt + suite wiring without a model call.
spb eval run prompts/typescript-coder.md --harness pi-agent \
  --suite evals/typescript-coder.yaml --dry-run

# Run direct model calls and DeepEval metrics.
spb eval run prompts/typescript-coder.md --harness pi-agent \
  --suite evals/typescript-coder.yaml
```

The selected `llm` model receives the compiled prompt as its system prompt and
each suite input as its user prompt. `judge_model` is required when a suite uses
`g_eval`; it must name an independent `llm` model or alias so the generation
model does not grade itself. Configure model credentials through `llm`
(for example `OPENAI_API_KEY`, `llm keys set`, or installed `llm` provider
plugins). DeepEval handles metric scoring through the configured `judge_model`
`llm` alias.

The first integration supports `answer_relevancy` and `g_eval` metrics. A
`g_eval` suite requires `expected_output` for every test because the metric
compares the generated response with that reference. It is single-turn and
direct-model only; harness tool execution, multi-turn tests, and trajectory
evaluation are later work.

Each completed run writes a YAML result artifact by default:

```text
build/evals/<prompt-name>/<version>/result.yaml
```

It records the prompt/version and rendered digest, suite digest, model,
per-test outputs, per-metric scores/reasons, and mean score. Use `--output` to
choose an exact result file, or `--fail-under` to make CI fail when the mean
metric score falls below a threshold:

```bash
spb eval run prompts/typescript-coder.md --harness pi-agent \
  --suite evals/typescript-coder.yaml --fail-under 0.75
```

### Compare compressed prompts

Compare the uncompressed prompt with a compressed variant using the same suite:

```bash
spb eval compare prompts/typescript-coder.md --harness pi-agent \
  --suite evals/typescript-coder.yaml \
  --compressor llmlingua --max-score-drop 0.05
```

The command writes `comparison.yaml` beside the evaluation result. It stores
both runs, their mean-score difference, the allowed score drop, and the pass
result. A comparison fails when compression lowers the mean score by more than
`--max-score-drop`. Use `--compressor none` to verify the comparison workflow
without loading a compression model.

### Benchmark prompt releases

Label each suite test with an optional `group` (default: `default`) to report
and gate meaningful scenario categories such as `safety` or `coding`. Benchmark
an individual prompt release or compare two prompt source files:

```bash
spb benchmark run prompts/coder-1.1.0.md --harness pi-agent \
  --suite evals/typescript-coder.yaml --fail-under 0.75 \
  --min-group-score safety=0.9

spb benchmark compare prompts/coder-1.0.0.md prompts/coder-1.1.0.md \
  --harness pi-agent --suite evals/typescript-coder.yaml \
  --max-score-drop 0.02 --max-group-score-drop safety=0.01
```

Benchmark artifacts are written under `build/benchmarks/<prompt-name>/<version>/`.
The comparison records the overall and per-group score drops. Both source paths
are rendered using the same harness, variables, and suite, preserving the
prompt versions and rendered hashes in the result artifacts.

## Roadmap

Promptfoo export, multi-turn evaluations, and real harness/tool simulation are
planned follow-on integrations.

## Development

[Just](https://just.systems/) provides a concise interface to common workflows:

```bash
just check             # format, lint, type check, and test
just run -- --help     # invoke the spb console script
just build             # check, then install the Homebrew formula from source
just release v0.1.1    # publish a pushed tag as a GitHub release
just docs              # build Sphinx HTML documentation
```

Before `just release`, commit the release version, create and push its annotated
tag, and ensure the working tree is clean. The recipe runs all quality gates,
checks that the tag exists on `origin`, then creates a GitHub release with
generated notes. `Formula/spb.rb` targets the current release tag.

The tool is written in Python and uses [Click](https://click.palletsprojects.com/)
for command-line parsing, [Mustache](https://mustache.github.io/) templates via
[Chevron](https://github.com/noahmorrison/chevron), and
[LLMLingua](https://github.com/microsoft/LLMLingua) for optional prompt
compression. Python dependencies are managed with Pipenv. LLMLingua is exposed
as the `llmlingua` package extra and is not installed for ordinary rendering.

The core implementation keeps configuration loading, provider resolution,
prompt composition, rendering, compression, evaluation, artifact writing, and
Click command handling as separate modules so each behavior can be tested
independently. Run local checks with `pipenv run test`, `pipenv run lint`,
`pipenv run format-check`, and `pipenv run typecheck`.

XML-style prompt parsing is not part of v1. A parser such as
[`sloppy-xml-py`](https://github.com/mitsuhiko/sloppy-xml-py) should only be
introduced once an XML-specific prompt feature has a documented use case.
