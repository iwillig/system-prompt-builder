# System Prompt Builder

System Prompt Builder (`spb`) composes reproducible, versioned system prompts
from Markdown, reusable skills, template variables, and harness-specific tool
metadata.

It can:

- validate prompt projects;
- render prompts for a selected agent harness;
- resolve local and commit-pinned Git skill providers;
- record prompt, skill, variable, and output provenance in YAML manifests;
- produce optional LLMLingua-compressed artifacts;
- evaluate prompt releases through direct model calls and DeepEval;
- compare prompt versions and compressed variants with score gates.

## Documentation

The complete documentation is published at:

**https://www.iwillig.me/system-prompt-builder/**

Use these pages as entry points:

- [Get started](https://www.iwillig.me/system-prompt-builder/introduction.html)
- [Initialize a project](https://www.iwillig.me/system-prompt-builder/initialization.html)
- [Project configuration](https://www.iwillig.me/system-prompt-builder/configuration.html)
- [Prompt authoring](https://www.iwillig.me/system-prompt-builder/prompts.html)
- [CLI reference](https://www.iwillig.me/system-prompt-builder/cli.html)
- [Evaluation and benchmarks](https://www.iwillig.me/system-prompt-builder/evaluation.html)
- [ECA integration](https://www.iwillig.me/system-prompt-builder/eca.html)
- [Development](https://www.iwillig.me/system-prompt-builder/development.html)
- [Changelog](CHANGELOG.md)

## Requirements

- Python 3.14 or later
- Git when using Git skill providers

## Install

Install the published command from PyPI with `uv`:

```bash
uv tool install system-prompt-builder
```

Upgrade an existing `uv` installation with:

```bash
uv tool upgrade system-prompt-builder
```

Alternatively, install and upgrade the command with `pipx`:

```bash
pipx install system-prompt-builder
pipx upgrade system-prompt-builder
```

For development, install the locked environment with Pipenv:

```bash
pipenv sync --dev
```

## Quick start

Initialize the current repository:

```bash
spb init
```

The command creates `.spb/config.yaml`, a valid starter prompt at
`.spb/prompts/project-assistant.md`, and `.spb/skills/local/`. It refuses to
overwrite an existing configuration or starter prompt.

Validate and render the prompt:

```bash
spb validate
spb render .spb/prompts/project-assistant.md --harness pi_agent
```

The render command writes:

```text
build/pi_agent/project-assistant.md
build/pi_agent/project-assistant.manifest.yaml
```

Link the rendered prompt into a Pi project:

```bash
spb link build/pi_agent/project-assistant.md .pi/SYSTEM.md
pi --approve
```

Pi reads `.pi/SYSTEM.md` after project trust is granted.

## Core model

A project has four main inputs:

1. `.spb/config.yaml` defines supported harnesses, tool metadata, and skill
   providers.
2. `.spb/prompts/*.md` contains versioned prompt sources with YAML front matter.
3. Skill providers supply reusable Markdown instructions.
4. Repeatable `--var NAME=VALUE` options provide declared template values.

`spb render` composes these inputs in deterministic order. It writes the full
prompt and a manifest containing source and output hashes, resolved skill
hashes, pinned Git revisions, harness identity, and non-secret variable values.

Prompt versions are author-managed semantic versions. If the rendered content
for an existing name, version, and harness changes, `spb` rejects the write
unless `--replace-release` is provided.

## Common commands

```bash
spb init [DIRECTORY] [--harness HARNESS]
spb validate
spb render PROMPT --harness HARNESS [--var NAME=VALUE]
spb link SOURCE DESTINATION
spb eval validate SUITE
spb eval run PROMPT --harness HARNESS --suite SUITE
spb eval compare PROMPT --harness HARNESS --suite SUITE
spb benchmark run PROMPT --harness HARNESS --suite SUITE
spb benchmark compare BASELINE CANDIDATE --harness HARNESS --suite SUITE
```

See the [CLI reference](https://www.iwillig.me/system-prompt-builder/cli.html)
for every option and default.

## Development

Run all local quality gates:

```bash
just check
```

Build the documentation with warnings treated as errors:

```bash
just docs
```

Build and validate the wheel and source distribution:

```bash
just package-check
```

The project uses Click, Chevron, PyYAML, pytest, Ruff, mypy, Sphinx, and
optional DeepEval, `llm`, and LLMLingua integrations.

## License

Copyright © 2026 Ivan Willig. Licensed under the
[GNU Affero General Public License v3.0 or later](LICENSE).
