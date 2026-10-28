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
       evaluation_steps:
         - Check whether the answer names a concrete bug.
         - Check whether the answer explains the bug's impact.
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
   Required for all evaluation suites. Both ``answer_relevancy`` and ``g_eval``
   use this ``llm`` model or alias for grading. Use an independent model so the
   generation model does not grade itself.

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

``evaluation_steps``
   Required non-empty list of grading steps. The same steps apply to every
   case and repeat, so DeepEval does not generate new steps for each score.
   Changing these steps changes the grading contract.

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
these cases. A trace mismatch fails ``eval run`` and ``eval compare`` and is
recorded in their artifacts. ``eval ablate`` records trace pass counts across
repeats and reports a verdict without failing the command.

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

Ablate fragments and sweep compression rates
---------------------------------------------

For fragment-based prompts, compare one fragment change at a time with a shared,
uncompressed baseline. Drop any selected fragment, or compress an alias listed
under ``compressible_fragments`` at several rates. Other fragments and the
layout stay unchanged.

Preview the variants and planned case generations without calling the model:

.. code-block:: console

   $ spb eval ablate .spb/prompts/coder.md --harness pi_agent \
       --suite .spb/evals/coder.yaml --mode both \
       --fragments routing --rates 0.5,0.3 --dry-run

To run the sweep, omit ``--dry-run``. The default is three repeats. A report
includes per-run scores, tool-call traces, case-and-metric deltas, and verdicts:
``REGRESSION``, ``INDETERMINATE``, or ``NO_REGRESSION_DETECTED``. The last
verdict applies only to the evaluated suite and does not establish that the
fragment is universally redundant or safe to compress. Fewer than three
repeats are exploratory and cannot yield ``NO_REGRESSION_DETECTED``.

A live run reports the current baseline or variant, repeat, case, and whether
it is generating an answer or judging a metric. If a run fails, the last
progress line identifies the stage; invalid judge JSON retries are also shown.
No partial report is written. After a successful run, the CLI shows the
baseline and variant mean scores and the
pass counts, median scores, and threshold for each reported metric reason.
It labels runs with fewer than three repeats as exploratory and warns when
equal scores have different pass flags. Read the detailed judge responses in
the YAML report before relying on such a verdict.

The preview count is ``(1 + variants) * repeats * cases``. It counts case
generations, not judge calls, retries, tokens, or total endpoint requests.
``--max-case-generations N`` rejects a plan above that count before model
calls. Rate is the fraction of fragment tokens the compressor aims to retain;
the report's reduction percentage measures characters, not tokens. Use
``--compressor none`` for an offline rate-path check. Findings are reported
without a CI failure gate.

Project walkthrough: inspect the routing fragment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This repository's Python assistant selects ``routing`` for compression.
The checkout's ``Justfile`` provides three bounded shortcuts:

.. code-block:: console

   $ just fragment-ablate-plan
   $ just fragment-rate-plan
   $ OPENAI_API_KEY="$HF_TOKEN" just fragment-ablate-live

The first command previews a drop with no compression model or evaluation
calls (102 planned case generations). The second previews two rates with local
LLMLingua and no evaluation calls (153 planned case generations). The third
**calls the evaluation endpoint** for a drop with three repeats, caps the plan
at 102 case generations, and writes a timestamped YAML artifact under
``build/evals/``. Credentials must be configured in the invoking environment;
no credential is stored in the recipe. Each recipe accepts an optional alias,
for example ``just fragment-ablate-plan rules``. Rate previews require an
alias listed under ``compressible_fragments`` and accept a second comma-separated
rates argument, for example ``just fragment-rate-plan routing 0.5,0.2``.
These fixed caps reject the run if the suite grows beyond its current size;
they do not cap judge requests or retries. Use the CLI directly for other
prompts, suites, modes, or limits.

To preview both transformations without loading a compression model, use the
CLI directly:

.. code-block:: console

   $ pipenv run spb eval ablate .spb/prompts/python-assistant.md \
       --suite .spb/evals/python-assistant-hf.yaml --harness pi_agent \
       --mode both --fragments routing --rates 0.5,0.3 \
       --compressor none --dry-run --max-case-generations 204

The suite has 17 cases. With three repeats, the shared baseline plus one drop
and two rate variants plan ``(1 + 3) * 3 * 17 = 204`` case generations. The
``none`` compressor leaves both rate variants unchanged, so they show zero
character reduction; this checks wiring, not compression quality. Omit
``--compressor none`` to preview actual LLMLingua output locally. A measured
rate-0.5 preview of ``routing`` reduced the whole composed prompt by 2.9% in
characters; the rate targets tokens *within that fragment*, not a 50% reduction
of the whole prompt.

When the endpoint is healthy, remove ``--dry-run`` and pass the token only in
the process environment:

.. code-block:: console

   $ OPENAI_API_KEY="$HF_TOKEN" pipenv run spb eval ablate \
       .spb/prompts/python-assistant.md \
       --suite .spb/evals/python-assistant-hf.yaml --harness pi_agent \
       --mode drop --fragments routing --repeats 3 \
       --max-case-generations 102 \
       --output build/evals/routing-ablation.yaml

This command is an example, **not a verified live result**. The output YAML
contains ``baseline_runs``, per-variant ``outcomes`` with raw ``runs`` and
``traces``, and a ``matrix`` with one row for each variant/case/metric. Read
``verdict`` alongside ``reasons`` and ``exploratory`` in each outcome. A
``REGRESSION`` is an observed majority failure against a stable baseline;
``INDETERMINATE`` means the evidence is insufficient. Even
``NO_REGRESSION_DETECTED`` applies only to this suite. A preview does not
validate the endpoint-backed path.

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
