#!/usr/bin/env bash
set -euo pipefail

# Serves the cached GGUF model through llama.cpp's OpenAI-compatible API.
exec llama-server \
  --hf-repo unsloth/Qwen3.6-35B-A3B-GGUF:Q8_0 \
  --offline \
  --port "${LLAMA_PORT:-8080}" \
  --alias spb-local-qwen
