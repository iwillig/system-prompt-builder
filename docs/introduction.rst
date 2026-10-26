Use a prompt with Pi
====================

This guide creates a project prompt, renders it, and starts Pi with that prompt.

After the first PyPI release, install the command:

.. code-block:: console

   $ uv tool install system-prompt-builder

1. Create ``.spb/config.yaml``:

   .. code-block:: yaml

      version: 1
      support-harness: [pi-agent]
      tool-provider-metadata:
        pi-agent:
          tools: []
      skill-providers: []

2. Create ``prompts/project-assistant.md``:

   .. code-block:: markdown

      ---
      name: Project assistant
      version: 1.0.0
      skills: []
      ---
      Work on this project.
      Read the relevant files before making changes.
      Run the checks that cover your changes.

3. Render the prompt and link it into Pi's project configuration:

   .. code-block:: console

      $ spb render prompts/project-assistant.md --harness pi-agent
      build/pi-agent/project-assistant.md
      $ spb link build/pi-agent/project-assistant.md .pi/SYSTEM.md
      .pi/SYSTEM.md

4. Start Pi from the project root:

   .. code-block:: console

      $ pi --approve

Pi reads ``.pi/SYSTEM.md`` as the project system prompt after project trust is
granted. Edit the source prompt, increase its version, then render and link it
again when you change the instructions.
