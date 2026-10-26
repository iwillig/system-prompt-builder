Prompt authoring
================

A prompt is a Markdown file with YAML front matter. The front matter identifies
the prompt release, imported skills, and declared template variables. The body
is rendered with Mustache.

Prompt format
-------------

.. code-block:: markdown

   ---
   name: TypeScript coder
   version: 1.0.0
   rationale: Coding-agent prompt for TypeScript work.
   skills:
     - local/code-review
     - team/typescript
   variables:
     project_name:
       required: true
     response_style:
       default: concise
   ---
   You are a coding agent for {{{project_name}}}.
   You are running in {{harness.name}}.

   {{#tools}}
   - `{{name}}`: {{summary}}
   {{/tools}}

Front matter
------------

``name``
   Required non-empty prompt name. It is recorded in manifests and evaluation
   artifacts.

``version``
   Required semantic version. Pre-release and build metadata are accepted.

``rationale``
   Optional author metadata. The current renderer validates no behavior from
   this field and does not include it in the artifact manifest.

``skills``
   Optional ordered list of provider-qualified references. Each reference uses
   ``provider/skill-name`` and resolves to one Markdown file. Skills are
   appended after the rendered prompt body in the listed order.

``variables``
   Optional mapping of variable declarations. Each declaration must contain
   exactly one of ``required: true`` or ``default: <value>``.

Template context
----------------

The Mustache context contains:

``harness.name``
   Harness selected by ``--harness``.

``tools``
   Tool mappings configured for the selected harness.

Declared variables
   Values supplied through ``--var NAME=VALUE`` or taken from front matter
   defaults.

Mustache escapes ``{{variable}}`` as HTML. Use ``{{{variable}}}`` when the
value must remain plain text in the generated prompt.

Variable rules
--------------

Variable names must match ``[A-Za-z_][A-Za-z0-9_]*``. ``harness`` and ``tools``
are reserved.

Every value supplied with ``--var`` must have a declaration. Every required
variable must be supplied. A supplied value overrides a default. ``--var``
splits at the first equals sign, so values may contain additional equals signs.
Duplicate variable options are rejected.

Versioning and release collisions
---------------------------------

Use semantic versions to identify intended prompt behavior:

* Increase the patch version for corrections that preserve intent.
* Increase the minor version for backward-compatible instruction or skill
  changes.
* Increase the major version for changes to the role, expected behavior, or
  harness contract.

The version does not uniquely identify rendered bytes. The manifest also
records source, skill, and rendered SHA-256 digests.

If an existing artifact has the same prompt name, version, and harness but a
different rendered digest, rendering fails. Increase the prompt version, or use
``--replace-release`` when replacing the artifact is intentional.

Artifact layout
---------------

Rendering ``prompts/coder.md`` for ``pi-agent`` writes:

.. code-block:: text

   build/pi-agent/coder.md
   build/pi-agent/coder.manifest.yaml

With ``--compress``, it also writes:

.. code-block:: text

   build/pi-agent/coder.compressed.md

The manifest records:

* prompt name and version;
* source path and SHA-256 digest;
* selected harness;
* rendered prompt digest;
* visible template variables;
* names of redacted variables;
* resolved skill references, paths, and content digests;
* compression method, settings, and digest when compression is enabled.

Variable values are omitted when their names contain ``password``, ``secret``,
``token``, or ``key``. The manifest records those names under
``redacted_variables``.
