set shell := ["/bin/bash", "-cu"]

# List available recipes.
default:
    @just --list

# Run all local quality gates.
check: format-check lint typecheck test

# Run the same checks as the GitHub Actions CI workflow.
ci: check

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

# Build the Sphinx HTML documentation.
docs:
    pipenv run sphinx-build -W --keep-going -b html docs docs/_build/html

# Build the Slidy presentation about the spb CLI tools.
presentation:
    mkdir -p build/presentations
    pandoc --standalone --to slidy docs/presentations/spb-tools.md --output build/presentations/spb-tools.html

# Build a wheel and source distribution in dist/.
package:
    rm -rf dist
    pipenv run python -m build

# Validate the package metadata and install each distribution in a clean environment.
package-check: ci package
    pipenv run python -m twine check dist/*
    pipenv run ./scripts/check-distributions.sh dist

# Run the spb CLI; pass subcommands after `--`, e.g. `just run -- --help`.
run *args:
    pipenv run spb {{args}}

# Preview a one-fragment drop without evaluation or compression model calls.
fragment-ablate-plan alias="routing":
    pipenv run spb eval ablate .spb/prompts/python-assistant.md --suite .spb/evals/python-assistant-hf.yaml --harness pi_agent --mode drop --fragments {{quote(alias)}} --dry-run --max-case-generations 102

# Preview LLMLingua rates locally, without evaluation endpoint calls.
fragment-rate-plan alias="routing" rates="0.5,0.3":
    pipenv run spb eval ablate .spb/prompts/python-assistant.md --suite .spb/evals/python-assistant-hf.yaml --harness pi_agent --mode rate --fragments {{quote(alias)}} --rates {{quote(rates)}} --dry-run --max-case-generations 153

# Run a bounded live drop evaluation with HF_TOKEN as the model API key.
fragment-ablate-live alias="routing":
    OPENAI_API_KEY="${HF_TOKEN:?Set HF_TOKEN before running fragment-ablate-live}" pipenv run spb eval ablate .spb/prompts/python-assistant.md --suite .spb/evals/python-assistant-hf.yaml --harness pi_agent --mode drop --fragments {{quote(alias)}} --repeats 3 --max-case-generations 104 --output "build/evals/fragment-ablation-$(date -u +%Y%m%dT%H%M%SZ).yaml"

# Make this editable checkout the machine's default spb command.
install-dev:
    bash scripts/install-dev-command.sh

# Run quality gates and install the tagged release formula from source with Homebrew.
build: check
    brew install --build-from-source --formula ./Formula/spb.rb

# Publish an existing, pushed tag with notes from its changelog section.
release version: check
    test -z "$(git status --porcelain)"
    test "$(git rev-parse '{{version}}^{}')" = "$(git rev-parse HEAD)"
    git ls-remote --exit-code --tags origin "refs/tags/{{version}}" > /dev/null
    pipenv run python -m spb.release_notes "{{version}}" /tmp/spb-release-notes.md
    gh release create "{{version}}" --verify-tag --notes-file /tmp/spb-release-notes.md --title "{{version}}"
    rm -f /tmp/spb-release-notes.md
