# Run a local llama.cpp model

This runbook starts the repository's default local model and uses it for `spb` evaluations. It does not download a model or configure a remote provider.

## Prerequisites

Install `llama-server` from llama.cpp. The default model must already exist in the Hugging Face cache. Check the cache:

```bash
llama-server --cache-list
```

The launcher requires this cached model:

```text
unsloth/Qwen3.6-35B-A3B-GGUF:Q8_0
```

Install the evaluation dependencies:

```bash
pipenv run pip install '.[eval]'
```

## Start the server

Run the repository launcher in one terminal:

```bash
./scripts/run-local-llama.sh
```

The launcher starts llama.cpp with these settings:

- Model: `unsloth/Qwen3.6-35B-A3B-GGUF:Q8_0`
- Mode: offline
- Port: `8080`
- API model alias: `spb-local-qwen`

Check that the OpenAI-compatible API is available:

```bash
curl http://localhost:8080/v1/models
```

Set another port when needed:

```bash
LLAMA_PORT=8081 ./scripts/run-local-llama.sh
```

The host must have enough available memory to load the selected model. If the server cannot load it, choose a smaller cached GGUF model and update the launcher before running evaluations.

## Configure the `llm` Python library

Create or edit `~/.config/io.datasette.llm/extra-openai-models.yaml`:

```yaml
- model_id: spb-local-qwen
  model_name: spb-local-qwen
  api_base: http://localhost:8080/v1
```

When the server uses another port, set the matching `api_base` value.

Confirm that `llm` can resolve the model:

```bash
llm models -m spb-local-qwen
```

## Use the model in an evaluation suite

Set the suite model to the configured alias:

```yaml
model: spb-local-qwen
```

Validate the suite and prompt wiring before making a model call:

```bash
spb eval validate evals/typescript-coder.yaml
spb eval run prompts/typescript-coder.md --harness pi-agent \
  --suite evals/typescript-coder.yaml --dry-run
```

Run the evaluation after the server is ready:

```bash
spb eval run prompts/typescript-coder.md --harness pi-agent \
  --suite evals/typescript-coder.yaml
```

## Stop the server

Press `Ctrl+C` in the terminal that runs `scripts/run-local-llama.sh`.
