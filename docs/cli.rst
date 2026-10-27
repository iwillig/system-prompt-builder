CLI reference
=============

The ``spb`` command validates projects, renders prompts, links artifacts, and
runs evaluations and benchmarks.

Global command
--------------

.. code-block:: console

   $ spb --help

The command has no global configuration options. Commands that read a prompt
project accept ``--project-root`` where listed.

``spb init``
------------

Initialize a minimal prompt project in the selected directory. The directory is
created when needed. Initialization refuses to overwrite its configuration,
prompt, layout, or instruction fragment.

.. code-block:: console

   $ spb init [OPTIONS] [DIRECTORY]

.. list-table:: Arguments and options
   :header-rows: 1
   :widths: 24 18 58

   * - Value
     - Default
     - Usage
   * - ``DIRECTORY``
     - ``.``
     - Repository or directory that will contain the prompt project.
   * - ``--harness HARNESS``
     - ``pi_agent``
     - Initial harness name written to the project configuration.

The command creates ``.spb/config.yaml``,
``.spb/prompts/project-assistant.md``,
``.spb/layouts/project-assistant.md``,
``.spb/fragments/project_instructions/FRAGMENT.md``, and
``.spb/skills/local/``. See :doc:`initialization` for the generated
contents and workflow.

``spb validate``
----------------

Validate ``.spb/config.yaml`` and every Markdown prompt below ``.spb/prompts/``.
Validation checks prompt metadata, semantic versions, variable declarations,
selected fragment bundles and layout slots, skill references, provider
configuration, and at least one harness mapping.
Required runtime variable values are not needed during validation.

.. code-block:: console

   $ spb validate [--project-root DIRECTORY]

.. list-table:: Options
   :header-rows: 1
   :widths: 24 16 60

   * - Option
     - Default
     - Usage
   * - ``--project-root DIRECTORY``
     - ``.``
     - Directory containing ``.spb/config.yaml`` and ``.spb/prompts/``.

``spb render``
--------------

Render one prompt from ``.spb/prompts/`` into a harness-specific artifact
and manifest. When the prompt selects fragments, the manifest records each
fragment alias, source path, and digest.

.. code-block:: console

   $ spb render PROMPT --harness HARNESS [OPTIONS]

.. list-table:: Options
   :header-rows: 1
   :widths: 28 18 54

   * - Option
     - Default
     - Usage
   * - ``--harness HARNESS``
     - Required
     - Select a configured harness.
   * - ``--var NAME=VALUE``
     - None
     - Supply one declared template variable. Repeat for multiple values.
   * - ``--replace-release``
     - Disabled
     - Permit replacement when an existing artifact has changed bytes.
   * - ``--compress``
     - Disabled
     - Write a compressed prompt artifact in addition to the full prompt.
       Fragment-based prompts compress only ``compressible_fragments``
       aliases and require that key in the prompt's front matter.
   * - ``--compressor {none,llmlingua}``
     - ``llmlingua``
     - Select the compressor used with ``--compress``.
   * - ``--project-root DIRECTORY``
     - ``.``
     - Directory containing ``.spb/config.yaml``.

``none`` returns the original content and is useful for testing compression
plumbing. ``llmlingua`` requires the optional ``llmlingua`` dependency.

``spb link``
------------

Create an absolute symbolic link from a consumer path to a rendered artifact.
Parent directories are created when needed.

.. code-block:: console

   $ spb link SOURCE DESTINATION [--replace]

.. list-table:: Options
   :header-rows: 1
   :widths: 24 18 58

   * - Option
     - Default
     - Usage
   * - ``--replace``
     - Disabled
     - Remove an existing file or symbolic link at the destination first.

``spb eval validate``
---------------------

Validate an evaluation suite without loading a model.

.. code-block:: console

   $ spb eval validate SUITE

This command has no options.

``spb eval run``
----------------

Render a prompt, generate direct model responses, score them with DeepEval, and
write an evaluation result.

.. code-block:: console

   $ spb eval run PROMPT --suite SUITE --harness HARNESS [OPTIONS]

.. list-table:: Options
   :header-rows: 1
   :widths: 28 18 54

   * - Option
     - Default
     - Usage
   * - ``--suite PATH``
     - Required
     - Evaluation suite YAML file.
   * - ``--harness HARNESS``
     - Required
     - Harness used to render the prompt.
   * - ``--var NAME=VALUE``
     - None
     - Supply a declared prompt variable. Repeat as needed.
   * - ``--dry-run``
     - Disabled
     - Validate prompt and suite wiring without a model call or result file.
   * - ``--output PATH``
     - Generated path
     - Write the result to an exact file.
   * - ``--fail-under SCORE``
     - None
     - Fail when the overall mean score is below a value from 0 to 1.
   * - ``--project-root DIRECTORY``
     - ``.``
     - Directory containing ``.spb/config.yaml``.

The default output is
``build/evals/<prompt-name>/<version>/result.yaml``. The command also fails when
any metric reports that its required threshold was not met.

``spb eval compare``
---------------------

Compare the full prompt with a compressed variant using the same suite.

.. code-block:: console

   $ spb eval compare PROMPT --suite SUITE --harness HARNESS [OPTIONS]

.. list-table:: Options
   :header-rows: 1
   :widths: 30 18 52

   * - Option
     - Default
     - Usage
   * - ``--suite PATH``
     - Required
     - Evaluation suite YAML file.
   * - ``--harness HARNESS``
     - Required
     - Harness used to render the prompt.
   * - ``--var NAME=VALUE``
     - None
     - Supply a declared prompt variable. Repeat as needed.
   * - ``--compressor {none,llmlingua}``
     - ``llmlingua``
     - Compressor used for the candidate prompt.
   * - ``--max-score-drop SCORE``
     - ``0.0``
     - Maximum accepted baseline minus candidate mean score.
   * - ``--output PATH``
     - Generated path
     - Write the comparison to an exact file.
   * - ``--project-root DIRECTORY``
     - ``.``
     - Directory containing ``.spb/config.yaml``.

The default output is
``build/evals/<prompt-name>/<version>/comparison.yaml``.

``spb benchmark run``
---------------------

Evaluate one prompt release and gate its overall and per-group scores.

.. code-block:: console

   $ spb benchmark run PROMPT --suite SUITE --harness HARNESS [OPTIONS]

.. list-table:: Options
   :header-rows: 1
   :widths: 31 18 51

   * - Option
     - Default
     - Usage
   * - ``--suite PATH``
     - Required
     - Evaluation suite YAML file.
   * - ``--harness HARNESS``
     - Required
     - Harness used to render the prompt.
   * - ``--var NAME=VALUE``
     - None
     - Supply a declared prompt variable. Repeat as needed.
   * - ``--output PATH``
     - Generated path
     - Write the benchmark result to an exact file.
   * - ``--fail-under SCORE``
     - None
     - Fail when the overall mean score is below a value from 0 to 1.
   * - ``--min-group-score GROUP=SCORE``
     - None
     - Require a minimum mean score for a named test group. Repeat as needed.
   * - ``--project-root DIRECTORY``
     - ``.``
     - Directory containing ``.spb/config.yaml``.

The default output is
``build/benchmarks/<prompt-name>/<version>/result.yaml``.

``spb benchmark compare``
-------------------------

Evaluate two prompt source files with the same harness, variables, and suite,
then gate overall and per-group score regressions.

.. code-block:: console

   $ spb benchmark compare BASELINE CANDIDATE \
       --suite SUITE --harness HARNESS [OPTIONS]

.. list-table:: Options
   :header-rows: 1
   :widths: 34 18 48

   * - Option
     - Default
     - Usage
   * - ``--suite PATH``
     - Required
     - Evaluation suite YAML file.
   * - ``--harness HARNESS``
     - Required
     - Harness used to render both prompts.
   * - ``--var NAME=VALUE``
     - None
     - Supply a declared prompt variable to both prompts. Repeat as needed.
   * - ``--max-score-drop SCORE``
     - ``0.0``
     - Maximum accepted baseline minus candidate mean score.
   * - ``--max-group-score-drop GROUP=SCORE``
     - None
     - Maximum accepted score drop for a named group. Repeat as needed.
   * - ``--output PATH``
     - Generated path
     - Write the comparison to an exact file.
   * - ``--project-root DIRECTORY``
     - ``.``
     - Directory containing ``.spb/config.yaml``.

The default output is
``build/benchmarks/<candidate-name>/<candidate-version>/comparison.yaml``.
