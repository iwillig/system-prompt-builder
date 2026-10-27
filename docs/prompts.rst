Prompt authoring
================

A system prompt is a Markdown file with YAML front matter. The front matter
identifies its release, selected fragments, layout, imported skill text, and
declared variables. Its body is one Mustache template, a set of legacy inline
sections, or empty when the prompt selects reusable fragments.

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
   Optional mapping of variable declarations. Variable names must use lowercase
   ``snake_case``. Each declaration must contain exactly one of
   ``required: true`` or ``default: <value>``.

``layout``
   Optional path to a Markdown layout under ``.spb/layouts/``. When present,
   the layout places either inline sections or selected reusable fragments.
   See `Reusable prompt fragments`_ and `Sectioned prompts`_.

``fragments``
   Optional, non-empty mapping from lowercase ``snake_case`` aliases to
   directories under ``.spb/fragments/``. Requires a layout and an empty
   prompt body. See `Reusable prompt fragments`_.

Reusable prompt fragments
-------------------------

A system prompt selects reusable instruction bundles and gives each one an
alias. Only the system prompt selects fragments; fragment text cannot include
another fragment. A bundle contains ``FRAGMENT.md`` and optionally
``fragment.yaml`` with ``mode: template`` (the default) or ``mode: literal``.
A bundle with other files, such as imported skill resources, cannot currently
be used in a system prompt; it must first be adapted into a self-contained
fragment. Skill import and export are not yet implemented.

For example, put ``Hello {{{project_name}}}.`` in
``.spb/fragments/identity/FRAGMENT.md`` and define a prompt as:

.. code-block:: markdown

   ---
   name: Coding assistant
   version: 1.0.0
   layout: .spb/layouts/assistant.md
   fragments:
     identity: .spb/fragments/identity
   variables:
     project_name:
       required: true
   ---

Its separate layout chooses the placement:

.. code-block:: text

   <identity>
   {{{fragments.identity}}}
   </identity>

The renderer first renders template-mode fragment text with ``project`` from
``.spb/config.yaml``, harness, tools, and declared variables. Literal-mode text is not interpolated. It then renders
the layout with only the ``fragments`` mapping. A layout must use each selected
alias at least once, may repeat one, and may not reference an unselected alias.
Use triple-brace slots to avoid HTML-escaping Markdown. The renderer removes
one trailing newline from each rendered fragment so the layout owns the
whitespace around it. The manifest records each selected alias, source path,
rendering mode, and SHA-256 digest. Existing ``skills:`` references still append skill text;
they do not import or export skill packages.

Sectioned prompts
------------------

The existing inline-section format remains supported. A prompt body can group
its Markdown into named, XML-like sections and let a layout template decide
the rendered order. This format applies when a layout is declared without a
``fragments`` mapping. Without either feature, the body is one Mustache
template.

A sectioned prompt marks each block with a top-level pseudo-XML tag:

.. code-block:: markdown

   ---
   name: Symbolic assistant
   version: 1.0.0
   layout: .spb/layouts/assistant.md
   variables:
     project_name:
       required: true
   ---
   <identity>
   You are a coding agent for {{{project_name}}}.
   </identity>

   <rules>
   1. Work in {{harness.name}}.
   2. Read source before changing it.
   </rules>

The layout under ``.spb/layouts/`` receives each section as an already
rendered value:

.. code-block:: text

   <rules>
   {{{sections.rules}}}
   </rules>

   <identity>
   {{{sections.identity}}}
   </identity>

Rendering works in two passes. First, each section renders with the full
template context: ``harness``, ``tools``, and declared variables. Second, the
layout renders with those rendered sections under the ``sections`` mapping.
The example layout reverses the source order, so the rendered prompt begins
with ``<rules>``.

Mustache does not expand tags inside an interpolated value, which is why the
two passes cannot be merged into one. Triple-brace slots keep the section
text unescaped; ordinary ``{{sections.name}}`` interpolation would HTML-escape
the Markdown.

Section rules
~~~~~~~~~~~~~

* Section names use lowercase ``snake_case`` and each name may appear once.
* One newline directly after an opening tag and one directly before a closing
  tag are marker placement, not content. Every other character is preserved:
  blank lines, indentation, literal ``&``, the text ``&amp;``, and Unicode
  punctuation.
* XML-like tags are reserved for structure. Any additional tag inside a
  section, including a tag inside a Markdown code fence, is rejected. Section
  attributes, XML comments, processing instructions, and doctypes are rejected
  as well. Failures name the prompt path and a body line and column.
* Text outside sections, other than whitespace between them, is rejected.
* Section extraction performs no XML entity resolution and no escaping, so
  authors never write CDATA or ``&lt;`` to keep Markdown intact.

Layout rules
~~~~~~~~~~~~

* A layout is a Markdown file under ``.spb/layouts/``, referenced by the
  front-matter ``layout`` path.
* The layout must reference every section exactly once through an unescaped
  ``{{{sections.<name>}}}`` slot, and must not reference a section the prompt
  does not define.
* One trailing newline is removed from each rendered section before
  insertion, so the layout owns the whitespace around section boundaries.
* The layout renders with only the ``sections`` mapping. Harness details,
  tools, and variables belong inside section bodies.
* ``sections`` is a reserved name in prompt variable declarations and in
  ``--var``.

When a layout is used, the artifact manifest records the layout path and the
SHA-256 digest of the layout text next to the existing source and rendered
digests.

Why use sections
~~~~~~~~~~~~~~~~

* **Readable sources.** Sections hold plain Markdown. No CDATA blocks and no
  ``&lt;``-style escaping are needed to keep prose, lists, and code fences
  intact.
* **Order independence.** Authors add or reorder sections freely; the layout
  fixes the rendered order. Reordering or highlighting a section becomes a
  layout edit that leaves prompt prose untouched.
* **Separation of content and arrangement.** The same sectioned source can be
  composed differently by a different layout, so structural experiments do
  not rewrite instructions.
* **Honest failure.** Duplicate, mismatched, or unclosed section markers and
  out-of-section prose fail validation with a source location instead of
  rendering something the author did not write.

Template context
----------------

The Mustache context contains:

``harness.name``
   Harness selected by ``--harness``.

``tools``
   Tool mappings configured for the selected harness.

``project``
   The ``project_name`` value from ``.spb/config.yaml``. When no project name
   is configured, this Mustache lookup is empty.

Declared variables
   Values supplied through ``--var NAME=VALUE`` or taken from front matter
   defaults.

``sections.<name>``
   Rendered inline-section text, available to a legacy sectioned layout.
   Not available inside a section body, and not a valid variable name.

``fragments.<alias>``
   Rendered text from a fragment selected by the system prompt, available only
   to its layout. Not available inside fragment text or as a variable name.

Mustache escapes ``{{variable}}`` as HTML. Use ``{{{variable}}}`` when the
value must remain plain text in the generated prompt.

Variable rules
--------------

Variable names must use lowercase ``snake_case``. ``harness``, ``tools``,
``sections``, ``fragments``, and ``project`` are reserved.

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
records source, layout, fragment, skill, and rendered SHA-256 digests.

An existing output path with a different rendered digest requires
``--replace-release`` even when the prompt version changes. Increase the
version when prompt behavior changes, then use that flag to confirm replacing
the existing file. An idempotent render with the same digest does not need it.

Artifact layout
---------------

Rendering ``.spb/prompts/coder.md`` for ``pi_agent`` writes:

.. code-block:: text

   build/pi_agent/coder.md
   build/pi_agent/coder.manifest.yaml

With ``--compress``, it also writes:

.. code-block:: text

   build/pi_agent/coder.compressed.md

The manifest records:

* prompt name and version;
* source path and SHA-256 digest;
* selected harness;
* rendered prompt digest;
* visible template variables;
* names of redacted variables;
* resolved skill references, paths, and content digests;
* selected fragment aliases, source paths, content digests, and rendering modes;
* layout path and content digest when a layout is used;
* compression method, settings, and digest when compression is enabled.

Variable values are omitted when their names contain ``password``, ``secret``,
``token``, or ``key``. The manifest records those names under
``redacted_variables``.
