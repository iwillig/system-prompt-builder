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


def _fragment_project(tmp_path: Path) -> Path:
    from spb.initialization import initialize_project

    initialize_project(tmp_path, harness="pi_agent")
    (tmp_path / ".spb" / "layouts").mkdir(exist_ok=True)
    (tmp_path / ".spb" / "fragments" / "shared").mkdir(parents=True)
    (tmp_path / ".spb" / "fragments" / "shared" / "FRAGMENT.md").write_text(
        "Hello {{{project_name}}} in {{harness.name}}.\n", encoding="utf-8"
    )
    return tmp_path / ".spb" / "prompts" / "project-assistant.md"


def test_fragments_are_bound_by_prompt_and_placed_by_layout(tmp_path: Path) -> None:
    from spb.rendering import render_prompt, validate_project

    prompt = _fragment_project(tmp_path)
    (tmp_path / ".spb" / "layouts" / "one.md").write_text(
        "<rules>\n{{{fragments.greeting}}}\n</rules>\n"
        "<identity>\n{{{fragments.greeting}}}\n</identity>\n",
        encoding="utf-8",
    )
    prompt.write_text(
        "---\nname: Assistant\nversion: 1.0.0\n"
        "layout: .spb/layouts/one.md\n"
        "fragments: {greeting: .spb/fragments/shared}\n"
        "variables: {project_name: {default: Acme}}\n---\n",
        encoding="utf-8",
    )
    second = prompt.with_name("second.md")
    (tmp_path / ".spb" / "layouts" / "two.md").write_text(
        "# Identity\n{{{fragments.intro}}}\n", encoding="utf-8"
    )
    second.write_text(
        "---\nname: Second\nversion: 1.0.0\n"
        "layout: .spb/layouts/two.md\n"
        "fragments: {intro: .spb/fragments/shared}\n"
        "variables: {project_name: {required: true}}\n---\n",
        encoding="utf-8",
    )

    assert validate_project(tmp_path) == [prompt, second]
    result = render_prompt(tmp_path, prompt, harness="pi_agent")
    assert result.content == (
        "<rules>\nHello Acme in pi_agent.\n</rules>\n"
        "<identity>\nHello Acme in pi_agent.\n</identity>\n"
    )
    assert len(result.fragments) == 1
    assert result.fragments[0].alias == "greeting"
    assert result.fragments[0].sha256
    assert (
        render_prompt(
            tmp_path, second, harness="pi_agent", variables={"project_name": "Other"}
        ).content
        == "# Identity\nHello Other in pi_agent.\n"
    )


@pytest.mark.parametrize(
    ("layout", "error"),
    [
        ("{{{fragments.other}}}", "missing fragment"),
        ("{{{fragments.greeting}}} {{{fragments.other}}}", "missing fragment"),
        ("plain text", "fragments.greeting"),
        ("{{fragments.greeting}}", "unescaped"),
        ("{{#fragments.greeting}}yes{{/fragments.greeting}}", "unescaped"),
    ],
)
def test_fragment_layout_rejects_invalid_slots(
    tmp_path: Path, layout: str, error: str
) -> None:
    from spb.rendering import validate_project

    prompt = _fragment_project(tmp_path)
    (tmp_path / ".spb" / "layouts" / "one.md").write_text(layout, encoding="utf-8")
    prompt.write_text(
        "---\nname: Assistant\nversion: 1.0.0\n"
        "layout: .spb/layouts/one.md\n"
        "fragments: {greeting: .spb/fragments/shared}\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=error):
        validate_project(tmp_path)


def test_fragment_rejects_nested_lookup_and_resource_bundle(tmp_path: Path) -> None:
    from spb.rendering import validate_project

    prompt = _fragment_project(tmp_path)
    (tmp_path / ".spb" / "layouts" / "one.md").write_text(
        "{{{fragments.greeting}}}", encoding="utf-8"
    )
    prompt.write_text(
        "---\nname: Assistant\nversion: 1.0.0\n"
        "layout: .spb/layouts/one.md\n"
        "fragments: {greeting: .spb/fragments/shared}\n---\n",
        encoding="utf-8",
    )
    fragment = tmp_path / ".spb" / "fragments" / "shared" / "FRAGMENT.md"
    fragment.write_text("{{{fragments.other}}}", encoding="utf-8")
    with pytest.raises(ValueError, match="compose other fragments"):
        validate_project(tmp_path)
    fragment.write_text("Hello.\n", encoding="utf-8")
    (fragment.parent / "references").mkdir()
    (fragment.parent / "references" / "notes.md").write_text("Resource")
    with pytest.raises(ValueError, match="resource"):
        validate_project(tmp_path)


def test_fragment_rejects_path_escape_and_prompt_body(tmp_path: Path) -> None:
    from spb.rendering import validate_project

    prompt = _fragment_project(tmp_path)
    (tmp_path / ".spb" / "layouts" / "one.md").write_text(
        "{{{fragments.greeting}}}", encoding="utf-8"
    )
    prompt.write_text(
        "---\nname: Assistant\nversion: 1.0.0\n"
        "layout: .spb/layouts/one.md\n"
        "fragments: {greeting: ../outside}\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="under .spb/fragments"):
        validate_project(tmp_path)
    prompt.write_text(
        prompt.read_text(encoding="utf-8").replace(
            "../outside", ".spb/fragments/shared"
        )
        + "Unexpected body\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="body must be empty"):
        validate_project(tmp_path)


def test_literal_fragment_preserves_mustache_examples(tmp_path: Path) -> None:
    from spb.rendering import render_prompt

    prompt = _fragment_project(tmp_path)
    bundle = tmp_path / ".spb" / "fragments" / "shared"
    (bundle / "fragment.yaml").write_text("mode: literal\n", encoding="utf-8")
    (bundle / "FRAGMENT.md").write_text(
        "Use {{harness.name}} literally.\n", encoding="utf-8"
    )
    (tmp_path / ".spb" / "layouts" / "one.md").write_text(
        "{{{fragments.greeting}}}\n", encoding="utf-8"
    )
    prompt.write_text(
        "---\nname: Assistant\nversion: 1.0.0\n"
        "layout: .spb/layouts/one.md\n"
        "fragments: {greeting: .spb/fragments/shared}\n---\n",
        encoding="utf-8",
    )
    assert render_prompt(tmp_path, prompt, harness="pi_agent").content == (
        "Use {{harness.name}} literally.\n"
    )


def test_fragment_symlink_outside_root_is_rejected(tmp_path: Path) -> None:
    from spb.rendering import validate_project

    prompt = _fragment_project(tmp_path)
    (tmp_path / ".spb" / "layouts" / "one.md").write_text(
        "{{{fragments.greeting}}}", encoding="utf-8"
    )
    prompt.write_text(
        "---\nname: Assistant\nversion: 1.0.0\n"
        "layout: .spb/layouts/one.md\n"
        "fragments: {greeting: .spb/fragments/escape}\n---\n",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "fragments" / "escape").symlink_to(
        tmp_path / ".spb" / "fragments" / "shared", target_is_directory=True
    )
    with pytest.raises(ValueError, match="under .spb/fragments"):
        validate_project(tmp_path)


def test_python_assistant_identity_uses_config_project() -> None:
    from spb.rendering import render_prompt

    root = Path(__file__).resolve().parents[1]
    result = render_prompt(
        root, root / ".spb" / "prompts" / "python-assistant.md", harness="pi_agent"
    )
    assert len(result.fragments) == 10
    assert "built_in_tools" in result.rendered_fragments
    assert "`read`: Read a file's contents" in result.content
    assert result.version == "0.1.3"
    assert "<version>\n0.1.3\n</version>" in result.content
    assert result.content.startswith(
        "<identity>\nYou are a Python coding agent for system_prompt_builder, "
        "running in pi_agent.\n"
    )


def test_fragments_require_layout_and_reject_reserved_variable(tmp_path: Path) -> None:
    from spb.rendering import render_prompt, validate_project

    prompt = _fragment_project(tmp_path)
    prompt.write_text(
        "---\nname: Assistant\nversion: 1.0.0\n"
        "fragments: {greeting: .spb/fragments/shared}\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="require a layout"):
        validate_project(tmp_path)

    (tmp_path / ".spb" / "layouts" / "one.md").write_text(
        "{{{fragments.greeting}}}", encoding="utf-8"
    )
    prompt.write_text(
        "---\nname: Assistant\nversion: 1.0.0\n"
        "layout: .spb/layouts/one.md\n"
        "fragments: {greeting: .spb/fragments/shared}\n"
        "variables: {fragments: {default: bad}}\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="reserved"):
        render_prompt(tmp_path, prompt, harness="pi_agent")


def test_project_assistant_fragment_migration_preserves_rendered_bytes() -> None:
    import hashlib

    from spb.rendering import render_prompt

    root = Path(__file__).resolve().parents[1]
    result = render_prompt(
        root, root / ".spb" / "prompts" / "project-assistant.md", harness="pi_agent"
    )
    assert [fragment.alias for fragment in result.fragments] == ["instructions"]
    assert hashlib.sha256(result.content.encode("utf-8")).hexdigest() == (
        "fa05b636972a95e9edc71933bc9565fe421d23f82001604c23667e41f96c9e48"
    )


def test_render_prompt_exposes_config_project_to_fragments(tmp_path: Path) -> None:
    from spb.initialization import initialize_project
    from spb.rendering import render_prompt

    project = initialize_project(tmp_path / "sample-app", harness="pi_agent")
    fragment = project.fragment
    fragment.write_text(
        "Working on {{project}} in {{harness.name}}.\n", encoding="utf-8"
    )

    result = render_prompt(project.root, project.prompt, harness="pi_agent")

    assert result.content == "Working on sample_app in pi_agent.\n"


def test_project_is_reserved_as_a_prompt_variable(tmp_path: Path) -> None:
    from spb.initialization import initialize_project
    from spb.rendering import render_prompt

    project = initialize_project(tmp_path, harness="pi_agent")
    project.prompt.write_text(
        project.prompt.read_text(encoding="utf-8").replace(
            "skills: []", "variables: {project: {default: fake}}\nskills: []"
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="reserved"):
        render_prompt(project.root, project.prompt, harness="pi_agent")


def test_validate_rejects_invalid_config_project_name(tmp_path: Path) -> None:
    from spb.initialization import initialize_project
    from spb.rendering import validate_project

    project = initialize_project(tmp_path, harness="pi_agent")
    import yaml

    config = yaml.safe_load(project.config.read_text(encoding="utf-8"))
    config["project_name"] = ""
    project.config.write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(ValueError, match="project_name must be a non-empty string"):
        validate_project(tmp_path)


def test_fragment_interpolation_does_not_html_escape_values(tmp_path: Path) -> None:
    import yaml

    from spb.initialization import initialize_project
    from spb.rendering import render_prompt

    project = initialize_project(tmp_path, harness="pi_agent")
    config = yaml.safe_load(project.config.read_text(encoding="utf-8"))
    config["project_name"] = "R&D_shop"
    project.config.write_text(yaml.safe_dump(config), encoding="utf-8")
    fragment = tmp_path / ".spb" / "fragments" / "custom"
    fragment.mkdir()
    (fragment / "FRAGMENT.md").write_text(
        "You work on {{{project}}} with {{project}}.\n", encoding="utf-8"
    )
    project.prompt.write_text(
        "---\nname: Assistant\nversion: 1.0.0\n"
        "layout: .spb/layouts/project-assistant.md\n"
        "fragments: {instructions: .spb/fragments/custom}\n---\n",
        encoding="utf-8",
    )

    result = render_prompt(tmp_path, project.prompt, harness="pi_agent")

    assert "You work on R&D_shop with R&amp;D_shop.\n" in result.content


def test_prompt_version_is_available_and_reserved(tmp_path: Path) -> None:
    from spb.initialization import initialize_project
    from spb.rendering import render_prompt

    project = initialize_project(tmp_path, harness="pi_agent")
    fragment = tmp_path / ".spb" / "fragments" / "custom"
    fragment.mkdir()
    (fragment / "FRAGMENT.md").write_text(
        "Version {{{version}}} in {{{harness.name}}}.\n", encoding="utf-8"
    )
    project.prompt.write_text(
        "---\nname: Assistant\nversion: 2.3.4\n"
        "layout: .spb/layouts/project-assistant.md\n"
        "fragments: {instructions: .spb/fragments/custom}\n---\n",
        encoding="utf-8",
    )

    result = render_prompt(tmp_path, project.prompt, harness="pi_agent")

    assert result.content == "Version 2.3.4 in pi_agent.\n"
    project.prompt.write_text(
        "---\nname: Assistant\nversion: 2.3.4\n"
        "layout: .spb/layouts/project-assistant.md\n"
        "fragments: {instructions: .spb/fragments/custom}\n"
        "variables: {version: {default: fake}}\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="reserved"):
        render_prompt(tmp_path, project.prompt, harness="pi_agent")
