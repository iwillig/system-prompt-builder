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

Run the editable checkout inside the Pipenv environment:

.. code-block:: console

   $ pipenv run spb --help
   $ pipenv run spb validate

To use the checkout as ``spb`` from any working directory, run:

.. code-block:: console

   $ just install-dev
   $ spb --help

The recipe installs development dependencies, refreshes the editable package,
removes a pipx installation of ``system-prompt-builder`` if present, and
creates ``~/bin/spb``. A link at ``~/.local/bin/spb`` makes it available when
``~/.local/bin`` is on ``PATH``. The launcher keeps the caller's working
directory, so ``spb validate`` acts on the project you are in. Re-run the
recipe after moving the checkout or changing its dependencies. It refuses to
replace a command at either path that belongs to another project. For the
published PyPI version instead, use the installation steps in :doc:`introduction`.

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

Record user-visible changes in ``CHANGELOG.md`` under ``Unreleased`` while
working. Before a release, move those entries into a version heading with the
release date, then update ``pyproject.toml`` and ``Formula/spb.rb`` to the same
version.

Run the package gate, create and push an annotated tag, then publish the
release:

.. code-block:: console

   $ just package-check
   $ git tag -a v0.3.0 -m "v0.3.0"
   $ git push origin v0.3.0
   $ just release v0.3.0

The release recipe reads the matching version section from ``CHANGELOG.md`` and
uses it as the GitHub release notes. The PyPI workflow then checks out the tag,
builds and validates the distributions, verifies that the tag is
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
   Configuration loading, prompt parsing, fragment resolution, variable
   resolution, skill provider resolution, and prompt composition.

``spb.sections``
   Extraction of legacy inline sections from pseudo-XML prompt bodies and
   their layout slot validation, built on the ``sloppy-xml`` parser.

``spb.compression``
   Optional prompt compression, including per-fragment compression of the
   aliases a prompt lists under ``compressible_fragments``.

``spb.evaluation``
   Suite loading, direct model calls, DeepEval scoring, result artifacts, and
   score comparisons.

``spb.cli``
   Click commands, artifact manifests, release collision checks, symbolic
   linking, and benchmark gates.

``spb.release_notes``
   Changelog section extraction for GitHub release notes.

System prompts use Markdown with YAML front matter. When front matter selects
``fragments``, the prompt body is empty and the layout receives rendered
fragment values. Without ``fragments``, a prompt with a layout uses inline
sections; a prompt without a layout renders its body directly. See
:doc:`prompts`.
