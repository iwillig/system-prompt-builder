# Changelog

All notable changes to System Prompt Builder are recorded in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/iwillig/system-prompt-builder/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/iwillig/system-prompt-builder/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/iwillig/system-prompt-builder/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/iwillig/system-prompt-builder/tree/v0.1.0
