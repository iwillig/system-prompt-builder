# Changelog

All notable changes to System Prompt Builder are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Added `just install-dev` to run the editable checkout as `spb` from any
  directory, without keeping a separate pipx copy on the same command name.
- System prompts can select reusable fragments and place them through a
  separate layout. The manifest records each fragment's source and digest.
- Template-mode fragments can use `{{project}}` to read `project_name` from
  project configuration.
- `--compress` now supports fragment-aware compression. Prompts using
  fragments list `compressible_fragments` aliases; only those fragments are
  compressed while all other text stays byte-identical. The manifest records
  the compressed aliases with input and output digests.
- Added `--compress-rate` to `spb render` and `spb eval compare` to set the
  target fraction of original tokens to keep (default 0.5). LLMLingua now
  loads one shared CPU-compatible model; override it with
  `SPB_LLMLINGUA_MODEL` and `SPB_LLMLINGUA_DEVICE`.

### Changed

- `spb init` now creates a starter prompt with a fragment and layout.
- The Python assistant prompt uses the configured project name in its identity.

## [0.3.0] - 2026-10-27

### Added

- Prompt bodies can group their Markdown into named pseudo-XML sections. A
  front-matter `layout` path selects a per-prompt layout under `.spb/layouts/`
  that arranges the rendered sections through `{{{sections.<name>}}}` slots.
  Section content is plain Markdown; XML-like tags are reserved for section
  structure. `sections` is now a reserved variable name, and manifests record
  the layout path and digest when a layout is used. Sections are extracted
  with the new `sloppy-xml` dependency without XML entity resolution or
  escaping.

### Changed

- The hosted documentation now uses the Furo theme, which follows the reader's
  color-scheme preference and provides a light and dark toggle.

## [0.2.1] - 2026-10-26

### Changed

- Prompt sources and local skills now live under `.spb/`. Move existing
  `prompts/` and `skills/` files there and update local provider paths and
  prompt arguments before validating or rendering.

## [0.2.0] - 2026-10-26

### Added

- Added `spb init` to create a safe starter project for a selected harness.
- Added a maintained changelog as the source for GitHub release notes.

### Changed

- Project configuration now requires snake_case keys, harness names, provider
  names, and prompt variable names. Existing projects must rename those fields
  and replace `pi-agent` with `pi_agent` in configuration and render commands.
  New artifacts use `build/pi_agent/`; existing artifacts are not moved.
- Published installation guidance now covers PyPI installation and upgrades
  with both `uv` and `pipx`.

## [0.1.1] - 2026-10-26

### Added

- Added PyPI packaging and trusted publishing through GitHub Actions.
- Added automatic publication of the Sphinx documentation site.
- Added ECA prompt and OpenTelemetry integration guidance.

### Changed

- Expanded the hosted documentation into user guides for configuration, prompt
  authoring, CLI usage, evaluation, integrations, and development.
- Added release checks that keep package versions, Git tags, and built
  distributions consistent.

## [0.1.0] - 2026-10-25

### Added

- Added prompt project validation and harness-specific rendering.
- Added local and commit-pinned Git skill providers.
- Added versioned artifact manifests with source, skill, variable, and rendered
  prompt provenance.
- Added optional LLMLingua compression and compression quality comparisons.
- Added direct-model DeepEval suites and versioned prompt benchmarks.
- Added symbolic linking for generated prompt artifacts.

[Unreleased]: https://github.com/iwillig/system-prompt-builder/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/iwillig/system-prompt-builder/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/iwillig/system-prompt-builder/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/iwillig/system-prompt-builder/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/iwillig/system-prompt-builder/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/iwillig/system-prompt-builder/tree/v0.1.0
