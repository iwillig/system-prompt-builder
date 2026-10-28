#!/usr/bin/env bash
set -euo pipefail

# Serves the cached GGUF model through llama.cpp's OpenAI-compatible API.
exec llama-server \
  --hf-repo unsloth/Qwen3.8-27B-GGUF:Q8_0 \
  --offline \
  --reasoning off \
  --ctx-size "${LLAMA_CTX_SIZE:-32768}" \
  --port "${LLAMA_PORT:-8080}" \
  --alias spb-local-qwen
