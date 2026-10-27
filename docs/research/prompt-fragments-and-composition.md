# Research: prompt fragments, compositions, and skills

This is a research snapshot from before fragment composition was implemented.
For current behavior, see [Prompt authoring](../prompts.rst).

## Conclusion

Model a system prompt as an identified composition of ordered prompt fragments. Keep a skill separate from an eagerly inserted fragment: an agent skill is a discoverable package that can be loaded on demand, while SPB currently appends the entire text of a selected skill to its rendered prompt. The relationship between a fragment and an exportable skill is a product decision, not an equivalence established by the source material. [SPB renderer][spb-renderer] [SPB CLI][spb-cli] [Agent Skills specification][agent-skills] [Anthropic skills overview][anthropic-skills]

## Primary-source findings

- OpenAI recommends keeping application prompts in code-managed, versioned helpers, using validated inputs and evaluating prompt changes as part of deployment. This supports treating composition and its inputs as versioned authoring objects; it does not prescribe a fragment format. [OpenAI prompting][openai-prompting]
- MCP prompt definitions have an identity (`name`), optional description, and arguments; retrieving one yields structured messages. MCP prompts are user-selectable templates, not necessarily system messages. Their identity-versus-rendered-content distinction is useful, but MCP prompts should not be treated as a direct file-format model for SPB. [MCP prompts][mcp-prompts]
- The Agent Skills specification defines a skill as a directory with a `SKILL.md` file containing metadata and instructions, optionally bundled with scripts, references, and assets. Anthropic describes staged loading: metadata is available for discovery, instructions load when triggered, and further resources load as needed. Embedding all skill text in a system prompt does not reproduce that loading behavior. [Agent Skills specification][agent-skills] [Anthropic skills overview][anthropic-skills]
- In SPB today, a prompt Markdown file owns name, version, optional layout, section bodies, and skill references. Sections render with variables and harness context, the layout positions them through `sections.<name>` slots, and resolved skill text is appended afterward. The CLI records source and rendered hashes and layout/skill provenance in the manifest. This is a linear assembly process, not recursive fragment composition or generation of skill packages. [SPB renderer][spb-renderer] [SPB sections][spb-sections] [SPB CLI][spb-cli]

## Candidate domain vocabulary for discussion

| Term | Proposed meaning | Distinction to preserve |
| --- | --- | --- |
| Prompt fragment | Named, reusable instruction bundle with optional resources. | Not necessarily a whole prompt or a skill. |
| System prompt | Identified, versioned composition that selects, orders, and configures fragments for a harness. | Source identity differs from rendered bytes. |
| Composition | The author-specified ordered uses of fragments, including parameter bindings and any literal framing. | Not merely a visual layout template. |
| Skill | Discoverable, optionally resource-bearing agent capability whose instructions may be loaded when relevant. | Not just appended prompt text. |
| Rendered artifact | Concrete text produced for a specific harness and bindings, with provenance. | Not the authored prompt definition. |

These are proposals, not descriptions of implemented SPB entities. A single authored instruction may have multiple outputs without making those outputs the same domain entity.

## Domain decisions

A fragment may contribute to a system prompt or be exported as a genuine, discoverable skill artifact. Only system prompts select fragments for composition; fragments do not include other fragments. The authored composition is flat, with no recursive fragment expansion. The layout remains separate: it inserts the system prompt's selected fragments as template values into its sections, but does not choose which fragments exist. Existing skills must be importable as full bundles (instructions plus scripts, references, assets, and other files) for re-export. A resource-dependent imported fragment cannot contribute to a system prompt until an author deliberately adapts it; copying only its instructions would leave resource references unusable. An LLM-assisted translation is a distinct, optional follow-up. These are intended domain rules, not claims about the current SPB implementation.

## Open questions

1. Is identity/version assigned to every reusable fragment, to the composition only, or both? An artifact still needs a content digest even when source versions are unchanged.
2. Are fragments intentionally harness-neutral until rendering, or may a fragment target one harness? That determines which object owns tool metadata and compatibility checks.
3. How should manually adapted prompt-safe fragments link back to their imported source? Bundle preservation is required for skill export, while prompt adaptation needs a reviewable relationship to the original.

[spb-renderer]: ../../src/spb/rendering.py
[spb-sections]: ../../src/spb/sections.py
[spb-cli]: ../../src/spb/cli.py
[agent-skills]: https://agentskills.io/specification
[anthropic-skills]: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
[mcp-prompts]: https://modelcontextprotocol.io/specification/2025-06-18/server/prompts
[openai-prompting]: https://developers.openai.com/api/docs/guides/prompting.md
