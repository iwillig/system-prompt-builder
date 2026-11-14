# Project assistant evaluation

`project-assistant.yaml` evaluates the prompt and harness selected in
`.spb/config.yaml`: `.spb/prompts/project-assistant.md` with `pi_agent`.
The cases cover clear writing, evidence-based debugging, Symbolic limitations,
the coding workflow, and Python testing. They include a request for a complete
Hegel example and a short answer about static analysis limits.

SPB sends one user message and a system prompt to a model for each case. It
does not run tools or check actual agent actions. The cases test responses and
plans, not whether the agent really used Symbolic, edited files, or ran tests.
Each metric applies to every case, so the suite uses one task-specific rubric
and a separate reference answer for each case. The judge reviews code as text;
it does not execute examples or enforce length limits deterministically. The
0.7 threshold is provisional, not a calibrated quality gate.

## Configure the remote model

Install SPB's optional evaluation dependencies in the project's Pipenv
environment:

```sh
pipenv run pip install '.[eval]'
```

Configure Simon Willison's `llm` to use the Hugging Face Inference Providers
OpenAI-compatible router. In `~/.config/io.datasette.llm/extra-openai-models.yaml`,
add this entry without removing other entries:

```yaml
- model_id: hf-glm
  model_name: zai-org/GLM-5.3-Flash
  api_base: https://router.huggingface.co/v1
  api_key_name: huggingface
```

Put a Hugging Face token with Inference Providers permission in `.spb/.env`:

```dotenv
SPB_LLM_KEY_HUGGINGFACE_ENDPOINT=your_token_here
```

This variable matches the local model entry's `api_key_name: huggingface-endpoint`.
If you use the example entry above with `api_key_name: huggingface`, use
`SPB_LLM_KEY_HUGGINGFACE` instead. SPB maps each `llm` key alias to an
uppercase environment variable prefixed with `SPB_LLM_KEY_`, replacing each
non-alphanumeric character with `_`. Aliases that normalize to the same name
share a variable. An environment key takes precedence over the stored `llm`
key. Do not put whitespace around the token value inside quotes.

The `.spb/.env` file contains plaintext secrets. It is ignored by this
repository's `.spb/.gitignore`; check your own project's Git rules before
adding credentials. Do not share the file or command output containing secrets.
Provider errors and tracebacks can expose credentials.

Run `pipenv run pip check` to check the environment for dependency conflicts.
If it reports conflicts, resolve them before relying on a live evaluation.
Check model availability and provider pricing before a live run. Remote
inference sends the system prompt, test inputs, generated outputs, and judge
instructions to the provider. Do not use
private content without permission. Model availability and account access may
vary. See the [Hugging Face chat API documentation](https://huggingface.co/docs/inference-providers/en/tasks/chat-completion)
and the [`llm` OpenAI-compatible model documentation](https://llm.datasette.io/en/stable/other-models.html#configure-an-openai-compatible-model).

## Validate and run

From the repository root, use the Justfile shortcuts:

```sh
just project-eval-deps      # Check Python dependencies
just project-eval-validate  # Validate the suite
just project-eval-plan      # Check the prompt and suite
just project-eval-live      # Run the evaluation
```

The validation and plan recipes make no model calls. The live recipe makes
remote calls.

The live run writes results under `.spb/build/evals/`. Inspect case outputs and judge
reasons before trusting the scores. The suite uses GLM-5.3-Flash for both
generation and judging, so the judge is not independent and may favor its own
responses. Use an independent judge and human review before treating results as
a release gate.

To compare the full prompt with the compressed variant currently used by Pi:

```sh
just project-eval-compare
```

This makes additional remote calls and recompresses the selected fragment; it
does not read `.pi/SYSTEM.md`. Compare its compression settings and resulting
prompt with the deployed artifact. A passing comparison does not prove that the
agent can perform real tool-based work.
