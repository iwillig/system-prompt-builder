Get started
===========

This guide installs ``spb``, creates a prompt project, renders one prompt, and
uses the result with Pi.

Requirements
------------

System Prompt Builder requires Python 3.14 or later. Git is also required when
a project uses Git skill providers.

Install from PyPI
-----------------

Install the published command with ``uv``:

.. code-block:: console

   $ uv tool install system-prompt-builder

Upgrade an existing ``uv`` installation with:

.. code-block:: console

   $ uv tool upgrade system-prompt-builder

Alternatively, install the command with ``pipx``:

.. code-block:: console

   $ pipx install system-prompt-builder

Upgrade an existing ``pipx`` installation with:

.. code-block:: console

   $ pipx upgrade system-prompt-builder

Confirm that the command is available:

.. code-block:: console

   $ spb --help

Create a project
----------------

Initialize the current repository:

.. code-block:: console

   $ spb init
   Initialized System Prompt Builder project in /path/to/example
     .spb/config.yaml
     prompts/project-assistant.md
     skills/local/

The starter project uses ``pi-agent``, contains a valid prompt with no required
variables, and includes a local skill directory. See :doc:`initialization` for
the generated contents, custom harness selection, and overwrite protection.

Validate and render
-------------------

Validate the project before rendering:

.. code-block:: console

   $ spb validate
   Validated 1 prompt(s).

Render the prompt for Pi:

.. code-block:: console

   $ spb render prompts/project-assistant.md --harness pi-agent
   build/pi-agent/project-assistant.md

The command also writes
``build/pi-agent/project-assistant.manifest.yaml``. The manifest identifies the
prompt version, source and output hashes, selected harness, variables, and
resolved skills.

Use the prompt with Pi
----------------------

Link the rendered artifact into Pi's project configuration:

.. code-block:: console

   $ spb link build/pi-agent/project-assistant.md .pi/SYSTEM.md
   .pi/SYSTEM.md

Start Pi from the project root:

.. code-block:: console

   $ pi --approve

Pi reads ``.pi/SYSTEM.md`` after project trust is granted. Edit the source
prompt, increase its semantic version, render it again, and update the link when
you change the instructions.

Next steps
----------

* Review initialization options in :doc:`initialization`.
* Define reusable local or Git skills in :doc:`configuration`.
* Add variables and Mustache sections with :doc:`prompts`.
* Review every command and option in :doc:`cli`.
* Test prompt behavior with :doc:`evaluation`.
