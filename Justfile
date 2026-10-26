set shell := ["/bin/bash", "-cu"]

# List available recipes.
default:
    @just --list

# Run all local quality gates.
check: format-check lint typecheck test

# Run the test suite.
test:
    pipenv run pytest

# Check code style and static errors.
lint:
    pipenv run ruff check .

# Verify formatting without modifying files.
format-check:
    pipenv run ruff format --check .

# Apply Ruff formatting.
format:
    pipenv run ruff format .

# Run strict static type checking.
typecheck:
    pipenv run mypy src

# Run the spb CLI; pass subcommands after `--`, e.g. `just run -- --help`.
run *args:
    pipenv run spb {{args}}

# Run quality gates and install the tagged release formula from source with Homebrew.
build: check
    brew install --build-from-source --formula ./Formula/spb.rb

# Publish an existing, pushed tag as a GitHub release with generated notes.
release version: check
    git diff --quiet
    git ls-remote --exit-code --tags origin "refs/tags/{{version}}" > /dev/null
    gh release create "{{version}}" --verify-tag --generate-notes --title "{{version}}"
