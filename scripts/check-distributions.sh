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
done
