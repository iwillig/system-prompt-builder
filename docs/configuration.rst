Project configuration
=====================

Every prompt project uses ``.spb/config.yaml`` to declare supported harnesses,
tool metadata, and skill providers. Paths in the configuration are resolved
from the project root passed through ``--project-root``.

Complete example
----------------

.. code-block:: yaml

   version: 1
   project_name: example_prompts
   author: Example team

   support_harness:
     - pi_agent
     - eca

   tool_provider_metadata:
     pi_agent:
       tools:
         - name: read
           summary: Read a file from the project.
         - name: bash
           summary: Execute a command in the project.
     eca:
       tools: []

   skill_providers:
     - name: local
       type: local
       path: skills/local

     - name: team
       type: git
       gitrepo: https://example.com/engineering/agent-skills.git
       revision: 0123456789abcdef0123456789abcdef01234567
       skill_root: skills

Configuration keys
------------------

Configuration field names, harness identifiers, and provider names must use
lowercase ``snake_case``. Free-text descriptions and paths keep their original
spelling. For existing projects, rename ``project-name`` to
``project_name``, ``support-harness`` to ``support_harness``,
``tool-provider-metadata`` to ``tool_provider_metadata``,
``skill-providers`` to ``skill_providers``, and ``skill-root`` to
``skill_root``. Replace the harness name ``pi-agent`` with ``pi_agent``
in configuration and in ``--harness`` arguments. Existing rendered artifacts
under ``build/pi-agent/`` are not moved; render again to write
``build/pi_agent/``.

``version``
   Configuration format version. The current format uses ``1``.

``project_name``
   Optional project metadata. It is not used during prompt rendering.

``author``
   Optional project metadata. It is not used during prompt rendering.

``support_harness``
   Required non-empty list used by project validation to identify supported
   harnesses. Add matching tool metadata for every harness used for rendering.

``tool_provider_metadata``
   Required mapping from harness name to harness metadata. Each harness may
   define a ``tools`` list. Tool entries are passed to the Mustache rendering
   context without additional schema transformation.

``skill_providers``
   List of named local or Git providers. It may be empty or omitted when prompts
   do not import skills.

Harness tool metadata
---------------------

A prompt can iterate over the selected harness's tool list:

.. code-block:: markdown

   {{#tools}}
   - `{{name}}`: {{summary}}
   {{/tools}}

``spb`` requires each tool entry to be a YAML mapping. The prompt decides which
fields it reads. ``name`` and ``summary`` are conventional fields rather than a
fixed tool schema.

Local skill providers
---------------------

A local provider reads Markdown files from a project directory:

.. code-block:: yaml

   skill_providers:
     - name: local
       type: local
       path: skills/local

The reference ``local/code-review`` resolves to
``skills/local/code-review.md``.

Local provider keys are:

``name``
   Provider name used before the slash in prompt skill references.

``type``
   Must be ``local``.

``path``
   Directory containing Markdown skill files, relative to the project root.

Git skill providers
-------------------

A Git provider reads skills from a pinned repository revision:

.. code-block:: yaml

   skill_providers:
     - name: team
       type: git
       gitrepo: https://example.com/engineering/agent-skills.git
       revision: 0123456789abcdef0123456789abcdef01234567
       skill_root: skills

Git provider keys are:

``name``
   Provider name used before the slash in prompt skill references.

``type``
   Must be ``git``.

``gitrepo``
   Repository clone URL.

``revision``
   Required immutable hexadecimal commit SHA between 40 and 64 characters.
   Branches and tags are rejected.

``skill_root``
   Directory containing Markdown skills inside the checked-out repository.

Git providers are cached under ``.spb/cache/<provider-name>``. Rendering checks
out the configured revision in detached mode. It records resolved Git skills
in ``.spb/skills.lock.yaml`` with their repository, revision, path, and SHA-256
content digest.

Generated project files
-----------------------

``.spb/cache/``
   Local Git provider checkouts.

``.spb/skills.lock.yaml``
   Resolved Git provider revisions and skill digests. Rendering updates entries
   for the Git providers used by the current prompt.

``build/``
   Rendered prompts, manifests, compressed variants, and evaluation artifacts.
