#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 DIST_DIRECTORY" >&2
  exit 2
fi

readonly dist_directory="$1"
readonly wheel="$(find "$dist_directory" -maxdepth 1 -name '*.whl' -print -quit)"
readonly source_distribution="$(find "$dist_directory" -maxdepth 1 -name '*.tar.gz' -print -quit)"

if [ -z "$wheel" ] || [ -z "$source_distribution" ]; then
  echo "Expected one wheel and one source distribution in $dist_directory" >&2
  exit 1
fi

readonly temporary_directory="$(mktemp -d)"
trap 'rm -rf "$temporary_directory"' EXIT

for distribution in "$wheel" "$source_distribution"; do
  environment="$temporary_directory/$(basename "$distribution")"
  python -m venv "$environment"
  "$environment/bin/python" -m pip install --disable-pip-version-check "$distribution"
  "$environment/bin/spb" --help > /dev/null

  project="$environment/smoke-test"
  mkdir -p "$project/.spb/prompts" "$project/.spb/layouts"
  cat > "$project/.spb/config.yaml" <<'YAML'
version: 1
support_harness: [pi_agent]
tool_provider_metadata:
  pi_agent:
    tools: []
skill_providers: []
YAML
  cat > "$project/.spb/prompts/demo.md" <<'MARKDOWN'
---
name: Section smoke test
version: 1.0.0
layout: .spb/layouts/demo.md
---
<rules>
Use A & B in {{harness.name}}.
</rules>

<identity>
You are a coding agent.
</identity>
MARKDOWN
  cat > "$project/.spb/layouts/demo.md" <<'MARKDOWN'
<identity>
{{{sections.identity}}}
</identity>

<rules>
{{{sections.rules}}}
</rules>
MARKDOWN
  cat > "$project/expected.md" <<'MARKDOWN'
<identity>
You are a coding agent.
</identity>

<rules>
Use A & B in pi_agent.
</rules>
MARKDOWN

  "$environment/bin/spb" validate --project-root "$project"
  "$environment/bin/spb" render "$project/.spb/prompts/demo.md" \
    --harness pi_agent --project-root "$project"
  diff -u "$project/expected.md" "$project/build/pi_agent/demo.md"
  grep -Fq 'layout:' "$project/build/pi_agent/demo.manifest.yaml"
done
