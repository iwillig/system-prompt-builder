Initialize a project
====================

``spb init`` creates a minimal System Prompt Builder project in an existing or
new directory. The command is non-interactive, defaults to the ``pi_agent``
harness, and does not overwrite managed files.

Create a project
----------------

Initialize the current repository:

.. code-block:: console

   $ spb init
   Initialized System Prompt Builder project in /path/to/example
     .spb/config.yaml
     prompts/project-assistant.md
     skills/local/

Initialize another directory:

.. code-block:: console

   $ spb init ../example

The directory is created when it does not exist.

Generated layout
----------------

The command creates this layout:

.. code-block:: text

   .spb/
     config.yaml
   prompts/
     project-assistant.md
   skills/
     local/

The configuration converts the directory name to snake_case for
``project_name``, declares the selected harness, and provides an empty tool
list:

.. code-block:: yaml

   version: 1
   project_name: example
   support_harness:
   - pi_agent
   tool_provider_metadata:
     pi_agent:
       tools: []
   skill_providers:
   - name: local
     type: local
     path: skills/local

The starter prompt is immediately valid and has no required variables:

.. code-block:: markdown

   ---
   name: Project assistant
   version: 1.0.0
   skills: []
   ---
   You are a coding agent running in {{harness.name}}.

   Read the relevant project files before making changes.
   Run the checks that cover your changes.

Select another harness
----------------------

Use ``--harness`` to select another harness name:

.. code-block:: console

   $ spb init --harness eca

The selected name is written to ``support_harness`` and
``tool_provider_metadata``. Add the harness's tool metadata to
``.spb/config.yaml`` before using tool sections in a prompt.

Overwrite protection
--------------------

Initialization fails before writing anything when either managed file already
exists:

* ``.spb/config.yaml``
* ``prompts/project-assistant.md``

The command reports every conflicting path. It does not provide a force option.
This protects an existing prompt project from accidental replacement.

Validate and render
-------------------

After initialization, validate and render the starter prompt:

.. code-block:: console

   $ spb validate
   Validated 1 prompt(s).
   $ spb render prompts/project-assistant.md --harness pi_agent
   build/pi_agent/project-assistant.md

Edit the configuration and prompt source to match the repository before using
the generated artifact in an agent harness.
