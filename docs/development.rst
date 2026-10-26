Development
===========

The development workflow uses Python 3.14, Pipenv, Just, pytest, Ruff, mypy,
and Sphinx.

Set up the environment
----------------------

Clone the repository and install development dependencies:

.. code-block:: console

   $ git clone https://github.com/iwillig/system-prompt-builder.git
   $ cd system-prompt-builder
   $ pipenv sync --dev

Quality gates
-------------

Run the same formatting, lint, type-checking, and test gates used by CI:

.. code-block:: console

   $ just check

The individual recipes are:

.. code-block:: console

   $ just format-check
   $ just lint
   $ just typecheck
   $ just test

Use ``just format`` to apply Ruff formatting.

Run the CLI
-----------

Run the editable console script inside the Pipenv environment:

.. code-block:: console

   $ pipenv run spb --help
   $ pipenv run spb validate

Build documentation
-------------------

Build the Sphinx site with warnings treated as errors:

.. code-block:: console

   $ just docs

The generated site is written to ``docs/_build/html``. Pushes to ``main``
deploy this directory through the GitHub Pages workflow.

Build distributions
-------------------

Build the wheel and source distribution:

.. code-block:: console

   $ just package

Run all quality gates, validate package metadata, and install both distribution
formats in clean environments:

.. code-block:: console

   $ just package-check

Release workflow
----------------

The PyPI workflow runs when a GitHub release is published. It checks out the
release tag, builds and validates the distributions, verifies that the tag is
``v<project-version>``, and publishes through PyPI trusted publishing.

The repository also contains a local Homebrew formula for the current release.
From a checkout, run:

.. code-block:: console

   $ just build

The recipe runs the quality gates and installs ``Formula/spb.rb`` from source.

Implementation boundaries
-------------------------

The source package separates these responsibilities:

``spb.rendering``
   Configuration loading, prompt parsing, variable resolution, skill provider
   resolution, and prompt composition.

``spb.compression``
   Optional prompt compression.

``spb.evaluation``
   Suite loading, direct model calls, DeepEval scoring, result artifacts, and
   score comparisons.

``spb.cli``
   Click commands, artifact manifests, release collision checks, symbolic
   linking, and benchmark gates.

XML-style prompt parsing is not supported. Markdown with YAML front matter is
the prompt source format.
