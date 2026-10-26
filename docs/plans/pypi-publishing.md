# Plan: publish `spb` to PyPI

**Status:** proposed  
**Goal:** publish the `system-prompt-builder` distribution through GitHub Actions
so users can install the `spb` command with pipx, uv, or pip.

## Decision

Use `system-prompt-builder` as the PyPI distribution name and `spb` as the
console command. The name is currently unregistered on PyPI.

Use TestPyPI for a release rehearsal. Use PyPI Trusted Publishing with GitHub
OIDC for TestPyPI and PyPI uploads. The workflows receive short-lived identity
tokens. No PyPI API token is stored in GitHub secrets.

The first public production release is `0.1.1`. The existing `v0.1.0` tag stays
unchanged.

## Scope

This plan adds package build, package validation, TestPyPI publication, and
PyPI publication.

This plan does not change the command interface, add optional evaluation or
compression dependencies to the base install, publish a Homebrew formula to
Homebrew/core, or broaden the declared Python support range.

## User contract

After a PyPI release, users install the command with one of these commands:

```console
$ uv tool install system-prompt-builder
$ pipx install system-prompt-builder
$ python -m pip install system-prompt-builder
```

Each installation provides:

```console
$ spb --help
```

The base distribution installs rendering, validation, linking, and benchmark
suite parsing. Evaluation and LLMLingua remain optional extras:

```console
$ uv tool install 'system-prompt-builder[eval]'
$ uv tool install 'system-prompt-builder[llmlingua]'
```

## Build and validation design

### Distribution metadata

Keep the existing PEP 621 metadata in `pyproject.toml`. Add the fields PyPI
uses to identify and route the project:

- `classifiers` for Python 3.14, AGPL-3.0-or-later, and the supported operating
  systems.
- `keywords` for prompt composition and coding agents.
- `project.urls` for the source repository, documentation site, issue tracker,
  and release notes.

Keep `requires-python = ">=3.14"`. CI validates that declared support level.
The package is pure Python, so one universal wheel and one source distribution
are sufficient.

### Local package commands

Add `build` and `twine` as development dependencies. Preserve `just build` for
the Homebrew formula. Add separate recipes:

```console
$ just package
$ just package-check
```

`just package` removes a prior `dist/` directory and runs `python -m build`.
`just package-check` runs `just ci`, builds the wheel and source distribution,
runs `twine check dist/*`, creates a temporary virtual environment, installs
the wheel, and checks `spb --help`.

The temporary environment must not use the repository checkout. This proves the
wheel contains the package and console entry point.

## GitHub Actions design

### Package validation

Extend CI or add a separate package-validation job on pull requests and pushes.
It runs `just package-check` and uploads `dist/` as an artifact. It has no PyPI
permissions.

### TestPyPI rehearsal

Add `.github/workflows/publish-testpypi.yaml` with `workflow_dispatch` only.
It builds from the selected commit, runs package validation, publishes to
TestPyPI through `pypa/gh-action-pypi-publish@release/v1`, then installs the
exact version in a clean environment from TestPyPI with PyPI as the dependency
index. It runs `spb --help` after installation.

The publish job uses:

```yaml
permissions:
  id-token: write
environment: testpypi
```

The TestPyPI install command must include the main PyPI index for runtime
dependencies:

```console
$ uv tool install \
    --index https://test.pypi.org/simple \
    --extra-index-url https://pypi.org/simple \
    system-prompt-builder==0.1.1
```

### Production publication

Add `.github/workflows/publish-pypi.yaml` for `release` events of type
`published`. It builds the release tag, runs `twine check`, and publishes the
distributions through `pypa/gh-action-pypi-publish@release/v1`.

The publish job uses:

```yaml
permissions:
  id-token: write
environment: pypi
```

Before publishing, the workflow checks that the Git tag exactly matches the
version in `pyproject.toml`, with a `v` prefix. For example, `v0.1.1` requires
project version `0.1.1`. This prevents an accidental upload from a tag that
names a different package version.

The existing `just release v0.1.1` command creates the GitHub Release after the
tag is pushed. Publishing that release triggers the PyPI workflow.

## Required account setup

The repository owner performs these one-time tasks before the TestPyPI run:

1. Create or use accounts on TestPyPI and PyPI.
2. Enable two-factor authentication on both accounts.
3. Register a pending Trusted Publisher on TestPyPI:
   - PyPI project name: `system-prompt-builder`
   - owner: `iwillig`
   - repository: `system-prompt-builder`
   - workflow: `publish-testpypi.yaml`
   - environment: `testpypi`
4. Register a pending Trusted Publisher on PyPI with the same owner,
   repository, and project name, using workflow `publish-pypi.yaml` and
   environment `pypi`.
5. Create GitHub environments named `testpypi` and `pypi`. Require manual
   approval for `pypi`.

PyPI permits pending Trusted Publishers for projects that are not yet
registered. The first successful upload claims the distribution name.

## Release procedure

1. Run `just package-check` locally.
2. Push the release candidate commit to `main`.
3. Dispatch the TestPyPI workflow for that commit.
4. Install the exact TestPyPI distribution with uv and run `spb --help`.
5. Create and push the annotated tag:

   ```console
   $ git tag -a v0.1.1 -m "Release v0.1.1"
   $ git push origin v0.1.1
   ```

6. Run `just release v0.1.1`.
7. Approve the `pypi` GitHub environment deployment.
8. Install the exact PyPI release with `uv tool install
   system-prompt-builder==0.1.1` and run `spb --help`.
9. Run `just build` and `brew test spb` after the `v0.1.1` tag exists.

## Acceptance criteria

- `just package-check` creates a wheel and source distribution and validates
  both metadata and a clean wheel installation.
- The TestPyPI workflow publishes through OIDC and the installed `spb` command
  runs.
- A published GitHub Release for a matching tag publishes the same version to
  PyPI through OIDC.
- The PyPI workflow has no stored PyPI credential.
- `uv tool install system-prompt-builder==<version>` installs a working `spb`
  command from PyPI.
- The release workflow rejects a Git tag whose version differs from the
  package version.

## Sources

- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
- [PyPA build frontend](https://build.pypa.io/)
- [Twine package checks](https://twine.readthedocs.io/en/stable/#twine-check)
