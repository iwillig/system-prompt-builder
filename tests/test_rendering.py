from pathlib import Path

import pytest


def test_render_prompt_composes_skills_and_harness_metadata(tmp_path: Path) -> None:
    from spb.rendering import render_prompt

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        """\
version: 1
support_harness:
  - pi_agent
tool_provider_metadata:
  pi_agent:
    tools:
      - name: read
        summary: Read a file.
skill_providers:
  - name: local
    type: local
    path: .spb/skills
""",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "skills").mkdir()
    (tmp_path / ".spb" / "skills" / "review.md").write_text(
        "Always explain review findings clearly.\n", encoding="utf-8"
    )
    (tmp_path / ".spb" / "prompts").mkdir()
    prompt_path = tmp_path / ".spb" / "prompts" / "coder.md"
    prompt_path.write_text(
        """\
---
name: Coder
version: 1.0.0
rationale: Help with code.
skills:
  - local/review
---
You are running in {{harness.name}}.
{{#tools}}Use {{name}}: {{summary}}{{/tools}}
""",
        encoding="utf-8",
    )

    result = render_prompt(tmp_path, prompt_path, harness="pi_agent")

    assert result.content == (
        "You are running in pi_agent.\n"
        "Use read: Read a file.\n\n"
        "Always explain review findings clearly.\n"
    )
    assert result.name == "Coder"
    assert result.version == "1.0.0"


def test_render_prompt_composes_sections_through_layout(tmp_path: Path) -> None:
    from spb.rendering import render_prompt

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        """\
version: 1
support_harness:
  - pi_agent
tool_provider_metadata:
  pi_agent:
    tools:
      - name: read
        summary: Read a file.
skill_providers: []
""",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "layouts").mkdir()
    (tmp_path / ".spb" / "layouts" / "assistant.md").write_text(
        "<rules>\n{{{sections.rules}}}\n</rules>\n\n"
        "<identity>\n{{{sections.identity}}}\n</identity>\n",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "prompts").mkdir()
    prompt_path = tmp_path / ".spb" / "prompts" / "assistant.md"
    prompt_path.write_text(
        """\
---
name: Assistant
version: 1.0.0
layout: .spb/layouts/assistant.md
variables:
  project_name:
    default: acme
---
<identity>
You are a coding agent for {{{project_name}}}.
</identity>

<rules>
Work in {{harness.name}}.
{{#tools}}
- `{{name}}`: {{summary}}
{{/tools}}
</rules>
""",
        encoding="utf-8",
    )

    result = render_prompt(tmp_path, prompt_path, harness="pi_agent")

    assert result.content == (
        "<rules>\nWork in pi_agent.\n- `read`: Read a file.\n</rules>\n\n"
        "<identity>\nYou are a coding agent for acme.\n</identity>\n"
    )
    assert result.layout is not None
    assert result.layout.path == tmp_path / ".spb" / "layouts" / "assistant.md"


def test_render_prompt_rejects_reserved_sections_variable(tmp_path: Path) -> None:
    from spb.rendering import render_prompt

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        "version: 1\nsupport_harness:\n  - pi_agent\n"
        "tool_provider_metadata:\n  pi_agent:\n    tools: []\nskill_providers: []\n",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "prompts").mkdir()
    prompt_path = tmp_path / ".spb" / "prompts" / "bad.md"
    prompt_path.write_text(
        """\
---
name: Bad
version: 1.0.0
variables:
  sections:
    default: x
---
<identity>
x
</identity>
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="reserved"):
        render_prompt(tmp_path, prompt_path, harness="pi_agent")


def test_render_prompt_rejects_layout_outside_layouts_directory(tmp_path: Path) -> None:
    from spb.rendering import render_prompt

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        "version: 1\nsupport_harness:\n  - pi_agent\n"
        "tool_provider_metadata:\n  pi_agent:\n    tools: []\nskill_providers: []\n",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "prompts").mkdir()
    prompt_path = tmp_path / ".spb" / "prompts" / "escape.md"
    prompt_path.write_text(
        """\
---
name: Escape
version: 1.0.0
layout: ../outside.md
---
<identity>
x
</identity>
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="layout"):
        render_prompt(tmp_path, prompt_path, harness="pi_agent")


def test_validate_project_rejects_markup_inside_sections(tmp_path: Path) -> None:
    from spb.rendering import validate_project

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        "version: 1\nsupport_harness:\n  - pi_agent\n"
        "tool_provider_metadata:\n  pi_agent:\n    tools: []\nskill_providers: []\n",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "layouts").mkdir()
    (tmp_path / ".spb" / "layouts" / "bad.md").write_text(
        "<identity>\n{{{sections.identity}}}\n</identity>\n", encoding="utf-8"
    )
    (tmp_path / ".spb" / "prompts").mkdir()
    (tmp_path / ".spb" / "prompts" / "bad.md").write_text(
        """\
---
name: Bad
version: 1.0.0
layout: .spb/layouts/bad.md
---
<identity>
```xml
<tool>read</tool>
```
</identity>
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="tags are reserved for sections"):
        validate_project(tmp_path)
