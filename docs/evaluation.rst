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

Create a YAML suite:

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

Validate and run
----------------

Validate a suite without model calls:

.. code-block:: console

   $ spb eval validate evals/coder.yaml

Validate prompt and suite wiring without a model call:

.. code-block:: console

   $ spb eval run prompts/coder.md --harness pi-agent \
       --suite evals/coder.yaml --dry-run

Run the suite:

.. code-block:: console

   $ spb eval run prompts/coder.md --harness pi-agent \
       --suite evals/coder.yaml --fail-under 0.75

The result records prompt and suite digests, model identity, visible variables,
resolved skills, generated outputs, metric scores and reasons, and the overall
mean score.

Compare a compressed prompt
---------------------------

Compare the full prompt with a compressed variant:

.. code-block:: console

   $ spb eval compare prompts/coder.md --harness pi-agent \
       --suite evals/coder.yaml --compressor llmlingua \
       --max-score-drop 0.05

Use ``--compressor none`` to test the comparison workflow without loading a
compression model.

Benchmark prompt releases
-------------------------

Benchmark one prompt and require a minimum score for a named group:

.. code-block:: console

   $ spb benchmark run prompts/coder-1.1.0.md --harness pi-agent \
       --suite evals/coder.yaml --fail-under 0.75 \
       --min-group-score safety=0.9

Compare two prompt source versions:

.. code-block:: console

   $ spb benchmark compare \
       prompts/coder-1.0.0.md prompts/coder-1.1.0.md \
       --harness pi-agent --suite evals/coder.yaml \
       --max-score-drop 0.02 \
       --max-group-score-drop safety=0.01

Both prompts use the same harness, variables, and suite. The comparison records
overall and per-group score drops.

Current boundaries
------------------

Evaluation is single-turn and direct-model only. It does not execute harness
tools, simulate agent trajectories, or run multi-turn conversations.

Local llama.cpp model
---------------------

The repository contains ``scripts/run-local-llama.sh`` for the cached
``unsloth/Qwen3.6-35B-A3B-GGUF:Q8_0`` model. The launcher exposes an
OpenAI-compatible endpoint on port 8080 with the ``spb-local-qwen`` alias.

Follow the complete setup and health-check procedure in the repository's
`local llama.cpp runbook <https://github.com/iwillig/system-prompt-builder/blob/main/docs/runbooks/local-llama-cpp.md>`_.
