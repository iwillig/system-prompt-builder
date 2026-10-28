Evaluation and benchmarks
=========================

System Prompt Builder can call a model through Simon Willison's ``llm`` library
and score the responses with DeepEval. Evaluation is optional and uses the
``eval`` package extra.

Install evaluation dependencies
-------------------------------

From a checkout, install the optional dependencies into the active environment:

.. code-block:: console

   $ pip install '.[eval]'

Configure generation and judge models through ``llm``. Credentials remain the
responsibility of the selected ``llm`` provider or plugin.

Evaluation suite format
-----------------------

Create a YAML suite under ``.spb/evals/``. ``spb init`` creates this empty
directory; suite paths outside it are also supported.


.. code-block:: yaml

   model: generation-model
   judge_model: independent-judge
   metrics:
     - type: answer_relevancy
       threshold: 0.7
     - type: g_eval
       name: Coding quality
       criteria: Identifies concrete bugs and explains their impact.
       threshold: 0.7
   tests:
     - name: reviews a function
       group: coding
       input: Review this function for bugs.
       expected_output: A concrete bug report.

Top-level keys
--------------

``model``
   Required ``llm`` model identifier used to generate each response.

``judge_model``
   Required when any metric has type ``g_eval``. Use an independent ``llm``
   model or alias so the generation model does not grade itself.

``metrics``
   Required non-empty list of metric definitions.

``tests``
   Required non-empty list of test cases.

Metric definitions
------------------

``answer_relevancy`` supports:

``type``
   Must be ``answer_relevancy``.

``threshold``
   Optional numeric pass threshold. The default is ``0.5``.

``g_eval`` supports:

``type``
   Must be ``g_eval``.

``name``
   Required metric name recorded in results.

``criteria``
   Required natural-language grading criteria.

``threshold``
   Optional numeric pass threshold. The default is ``0.5``.

A suite containing ``g_eval`` requires ``expected_output`` on every test.

Test cases
----------

``name``
   Required case name.

``group``
   Optional benchmark group. The default is ``default``.

``input``
   Required user message sent with the rendered prompt as the system prompt.

``expected_output``
   Optional reference output. It is required for every case when the suite uses
   ``g_eval``.

Mock configured tools
---------------------

A test case can offer selected configured tools to the model and return fixed
mock results. Each offered tool must have a ``parameters`` JSON Schema in the
selected harness's ``tool_provider_metadata``. The mock map keys are configured
tool names; each value is the string returned by that tool. No real tool code
runs.

Use ``expected_tool_calls`` to assert the full ordered call trace, including
each call's exact argument mapping. An empty list asserts that the model made no
tool calls. DeepEval receives both actual and expected tool traces when scoring
these cases. A trace mismatch fails the evaluation command and is recorded in
the result artifact.

.. code-block:: yaml

   tests:
     - name: reads the requested file
       input: Inspect src/example.py and explain what count_records returns.
       mock_tools:
         read: "def count_records(records): return len(records)"
       expected_tool_calls:
         - name: read
           arguments:
             path: src/example.py
       expected_output: It returns the number of records in its input list.

The tool schema is read from ``.spb/config.yaml`` for the chosen harness. A
case only offers tools listed under ``mock_tools``. Cases without
``mock_tools`` use direct model responses and do not send tool definitions.

Validate and run
----------------

Validate a suite without model calls:

.. code-block:: console

   $ spb eval validate .spb/evals/coder.yaml

Validate prompt and suite wiring without a model call:

.. code-block:: console

   $ spb eval run .spb/prompts/coder.md --harness pi_agent \
       --suite .spb/evals/coder.yaml --dry-run

Run the suite:

.. code-block:: console

   $ spb eval run .spb/prompts/coder.md --harness pi_agent \
       --suite .spb/evals/coder.yaml --fail-under 0.75

The result records prompt and suite digests, model identity, visible variables,
resolved skills, generated outputs, mock-tool call traces, metric scores and
reasons, and the overall mean score.

Compare a compressed prompt
---------------------------

Compare the full prompt with a compressed variant:

.. code-block:: console

   $ spb eval compare .spb/prompts/coder.md --harness pi_agent \
       --suite .spb/evals/coder.yaml --compressor llmlingua \
       --max-score-drop 0.05

Use ``--compressor none`` to test the comparison workflow without loading a
compression model.

For a prompt that uses fragments, ``spb eval compare`` compresses only the
aliases the prompt lists under ``compressible_fragments``. Add that front
matter key before comparing a fragment-based prompt; the comparison fails
without it.

Benchmark prompt releases
-------------------------

Benchmark one prompt and require a minimum score for a named group:

.. code-block:: console

   $ spb benchmark run .spb/prompts/coder-1.1.0.md --harness pi_agent \
       --suite .spb/evals/coder.yaml --fail-under 0.75 \
       --min-group-score safety=0.9

Compare two prompt source versions:

.. code-block:: console

   $ spb benchmark compare \
       .spb/prompts/coder-1.0.0.md .spb/prompts/coder-1.1.0.md \
       --harness pi_agent --suite .spb/evals/coder.yaml \
       --max-score-drop 0.02 \
       --max-group-score-drop safety=0.01

Both prompts use the same harness, variables, and suite. The comparison records
overall and per-group score drops.

Current boundaries
------------------

Evaluation uses one user turn and may run model-selected mock tools. It never
executes real harness tools, simulates multi-turn user conversations, or runs
full agent trajectories.

Hugging Face Inference Endpoint
-------------------------------

The project suite ``.spb/evals/python-assistant-hf.yaml`` targets the Hugging
Face endpoint through the ``spb-hf-qwen`` model alias. Add this entry to
``extra-openai-models.yaml`` in the directory returned by ``llm user_dir``:

.. code-block:: yaml

   - model_id: spb-hf-qwen
     model_name: /repository/Qwen3.8-27B-UD-Q4_K_M.gguf
     api_base: https://ogabjrf7kkaavl1f.endpoints.huggingface.cloud/v1/
     api_key_name: openai
     supports_tools: true

The model name is the ID returned by this endpoint's authenticated
``/v1/models`` response. Set ``supports_tools: true`` when the endpoint accepts
OpenAI-compatible tool calls; this enables tool schemas in the ``llm`` client.
``llm`` reads ``OPENAI_API_KEY`` for this custom model. If the token is stored
as ``HF_TOKEN``, pass it without writing it to the project configuration:

.. code-block:: console

   $ OPENAI_API_KEY="$HF_TOKEN" pipenv run llm -m spb-hf-qwen "Reply with pong"
   $ OPENAI_API_KEY="$HF_TOKEN" pipenv run spb eval run \
       .spb/prompts/python-assistant.md --harness pi_agent \
       --suite .spb/evals/python-assistant-hf.yaml

Keep the endpoint running while the evaluation runs. The suite uses the same
endpoint for generation and G-Eval judging, so each case makes requests for
both roles.

The repository contains ``scripts/run-local-llama.sh`` for the cached
``unsloth/Qwen3.8-27B-GGUF:Q8_0`` model. The launcher exposes an
OpenAI-compatible endpoint on port 8080 with the ``spb-local-qwen`` alias.
It disables reasoning for evaluation runs and defaults to a 32K-token context.

Follow the complete setup and health-check procedure in the repository's
`local llama.cpp runbook <https://github.com/iwillig/system-prompt-builder/blob/main/docs/runbooks/local-llama-cpp.md>`_.
