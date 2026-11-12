# Project assistant evaluation

`project-assistant.yaml` evaluates the prompt and harness selected in
`.spb/config.yaml`: `.spb/prompts/project-assistant.md` with `pi_agent`.
The cases cover clear writing, evidence-based debugging, Symbolic limitations,
the coding workflow, and Python testing.

SPB sends one user message and a system prompt to a model for each case. It
does not run tools or check actual agent actions. The cases test responses and
plans, not whether the agent really used Symbolic, edited files, or ran tests.
Each metric applies to every case, so the suite uses one task-specific rubric
and a separate reference answer for each case. The 0.7 threshold is provisional,
not a calibrated quality gate.

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

Store a Hugging Face token with Inference Providers permission using
`pipenv run llm keys set huggingface`; enter the token at the prompt, not in
this repository or a shell command. Check model availability and provider
pricing before a live run. Remote inference sends the system prompt, test
inputs, generated outputs, and judge instructions to the provider. Do not use
private content without permission. Model availability and account access may
vary. See the [Hugging Face chat API documentation](https://huggingface.co/docs/inference-providers/en/tasks/chat-completion)
and the [`llm` OpenAI-compatible model documentation](https://llm.datasette.io/en/stable/other-models.html#configure-an-openai-compatible-model).

## Validate and run

```sh
spb eval validate .spb/evals/project-assistant.yaml
spb eval run .spb/prompts/project-assistant.md --harness pi_agent \
  --suite .spb/evals/project-assistant.yaml --dry-run
spb eval run .spb/prompts/project-assistant.md --harness pi_agent \
  --suite .spb/evals/project-assistant.yaml
```

The first two commands make no model calls. The last command makes remote calls
and writes results under `.spb/build/evals/`. Inspect case outputs and judge
reasons before trusting the scores. The suite uses GLM-5.3-Flash for both
generation and judging, so the judge is not independent and may favor its own
responses. Use an independent judge and human review before treating results as
a release gate.

To compare the full prompt with the compressed variant currently used by Pi:

```sh
spb eval compare .spb/prompts/project-assistant.md --harness pi_agent \
  --suite .spb/evals/project-assistant.yaml --compressor llmlingua \
  --compress-rate 0.9 --max-score-drop 0.05
```

This makes additional remote calls and recompresses the selected fragment; it
does not read `.pi/SYSTEM.md`. Compare its compression settings and resulting
prompt with the deployed artifact. A passing comparison does not prove that the
agent can perform real tool-based work.
