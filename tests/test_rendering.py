from pathlib import Path


def test_render_prompt_composes_skills_and_harness_metadata(tmp_path: Path) -> None:
    from spb.rendering import render_prompt

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        """\
version: 1
support-harness:
  - pi-agent
tool-provider-metadata:
  pi-agent:
    tools:
      - name: read
        summary: Read a file.
skill-providers:
  - name: local
    type: local
    path: skills
""",
        encoding="utf-8",
    )
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "review.md").write_text(
        "Always explain review findings clearly.\n", encoding="utf-8"
    )
    (tmp_path / "prompts").mkdir()
    prompt_path = tmp_path / "prompts" / "coder.md"
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

    result = render_prompt(tmp_path, prompt_path, harness="pi-agent")

    assert result.content == (
        "You are running in pi-agent.\n"
        "Use read: Read a file.\n\n"
        "Always explain review findings clearly.\n"
    )
    assert result.name == "Coder"
    assert result.version == "1.0.0"
