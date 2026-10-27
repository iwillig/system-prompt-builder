# System Prompt Builder

This glossary names the intended domain for authoring reusable instructions and producing agent-facing outputs.

## Language

**Prompt fragment**:
A reusable instruction bundle that may include supporting resources. A fragment may contribute to a system prompt or serve as the source for a skill, but does not compose other fragments.
_Avoid_: Section, layout slot

**System prompt**:
An identified composition of prompt fragments intended as the agent's standing instructions. Only a system prompt selects fragments for composition.
_Avoid_: Layout, rendered text

**Layout**:
The arrangement of a system prompt's selected fragments into the final instruction text. A layout places fragments but does not select them.
_Avoid_: Fragment, system prompt

**Skill**:
A discoverable agent capability with instructions that the agent can load when relevant. A skill is a distinct output, not a fragment embedded in a system prompt.
_Avoid_: Appended skill text

**Rendered artifact**:
A concrete output of a system prompt composition or a skill export.
_Avoid_: Source fragment
