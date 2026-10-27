import subprocess
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner


def test_init_command_creates_a_valid_starter_project(tmp_path: Path) -> None:
    from spb.cli import cli

    project_root = tmp_path / "example"
    runner = CliRunner()

    result = runner.invoke(cli, ["init", str(project_root)])
    validation = runner.invoke(cli, ["validate", "--project-root", str(project_root)])
    rendering = runner.invoke(
        cli,
        [
            "render",
            str(project_root / ".spb" / "prompts" / "project-assistant.md"),
            "--harness",
            "pi_agent",
            "--project-root",
            str(project_root),
        ],
    )

    config = yaml.safe_load(
        (project_root / ".spb" / "config.yaml").read_text(encoding="utf-8")
    )
    prompt = (project_root / ".spb" / "prompts" / "project-assistant.md").read_text(
        encoding="utf-8"
    )
    assert result.exit_code == 0
    assert "Initialized System Prompt Builder project" in result.output
    assert config["project_name"] == "example"
    assert config["support_harness"] == ["pi_agent"]
    assert config["skill_providers"][0]["path"] == ".spb/skills/local"
    assert "layout: .spb/layouts/project-assistant.md" in prompt
    assert "instructions: .spb/fragments/project_instructions" in prompt
    assert "running in {{harness.name}}" in (
        project_root / ".spb" / "fragments" / "project_instructions" / "FRAGMENT.md"
    ).read_text(encoding="utf-8")
    assert (project_root / ".spb" / "layouts" / "project-assistant.md").read_text(
        encoding="utf-8"
    ) == "{{{fragments.instructions}}}\n"
    assert ".spb/fragments/project_instructions/FRAGMENT.md" in result.output
    assert ".spb/layouts/project-assistant.md" in result.output
    assert (project_root / ".spb" / "skills" / "local").is_dir()
    assert not (project_root / "prompts").exists()
    assert not (project_root / "skills").exists()
    assert validation.exit_code == 0
    assert "Validated 1 prompt(s)." in validation.output
    assert rendering.exit_code == 0
    artifact = project_root / "build" / "pi_agent" / "project-assistant.md"
    assert artifact.read_text(encoding="utf-8") == (
        "You are a coding agent running in pi_agent.\n\n"
        "Read the relevant project files before making changes.\n"
        "Run the checks that cover your changes.\n"
    )
    manifest = yaml.safe_load(artifact.with_suffix(".manifest.yaml").read_text())
    assert [item["alias"] for item in manifest["fragments"]] == ["instructions"]


def test_init_command_supports_a_custom_harness(tmp_path: Path) -> None:
    from spb.cli import cli

    result = CliRunner().invoke(cli, ["init", str(tmp_path), "--harness", "eca"])

    config = yaml.safe_load(
        (tmp_path / ".spb" / "config.yaml").read_text(encoding="utf-8")
    )
    assert result.exit_code == 0
    assert config["support_harness"] == ["eca"]
    assert config["tool_provider_metadata"] == {"eca": {"tools": []}}
    rendering = CliRunner().invoke(
        cli,
        [
            "render",
            str(tmp_path / ".spb" / "prompts" / "project-assistant.md"),
            "--harness",
            "eca",
            "--project-root",
            str(tmp_path),
        ],
    )
    assert rendering.exit_code == 0, rendering.output
    assert "running in eca" in (
        tmp_path / "build" / "eca" / "project-assistant.md"
    ).read_text(encoding="utf-8")


@pytest.mark.parametrize("harness", ["pi-agent", "piAgent"])
def test_init_requires_snake_case_harness(tmp_path: Path, harness: str) -> None:
    from spb.cli import cli

    result = CliRunner().invoke(cli, ["init", str(tmp_path), "--harness", harness])

    assert result.exit_code != 0
    assert "snake_case" in result.output
    assert not (tmp_path / ".spb").exists()


def test_init_command_refuses_to_overwrite_managed_files(tmp_path: Path) -> None:
    from spb.cli import cli

    config_path = tmp_path / ".spb" / "config.yaml"
    config_path.parent.mkdir()
    config_path.write_text("existing: true\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["init", str(tmp_path)])

    assert result.exit_code != 0
    assert ".spb/config.yaml" in result.output
    assert config_path.read_text(encoding="utf-8") == "existing: true\n"
    assert not (tmp_path / ".spb" / "prompts").exists()


def test_init_refuses_to_overwrite_a_prompt_under_spb(tmp_path: Path) -> None:
    from spb.cli import cli

    prompt_path = tmp_path / ".spb" / "prompts" / "project-assistant.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("Existing prompt.\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["init", str(tmp_path)])

    assert result.exit_code != 0
    assert ".spb/prompts/project-assistant.md" in result.output
    assert prompt_path.read_text(encoding="utf-8") == "Existing prompt.\n"
    assert not (tmp_path / ".spb" / "config.yaml").exists()
    assert not (tmp_path / ".spb" / "layouts").exists()
    assert not (tmp_path / ".spb" / "fragments").exists()


@pytest.mark.parametrize(
    "existing_path",
    [
        ".spb/layouts/project-assistant.md",
        ".spb/fragments/project_instructions/FRAGMENT.md",
        ".spb/fragments/project_instructions",
    ],
)
def test_init_refuses_to_overwrite_layout_or_fragment(
    tmp_path: Path, existing_path: str
) -> None:
    from spb.cli import cli

    path = tmp_path / existing_path
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix:
        path.write_text("existing\n", encoding="utf-8")
    else:
        path.mkdir()
    result = CliRunner().invoke(cli, ["init", str(tmp_path)])

    assert result.exit_code != 0
    assert existing_path in result.output
    assert not (tmp_path / ".spb" / "config.yaml").exists()
    assert not (tmp_path / ".spb" / "prompts").exists()
    assert path.exists()


def test_validate_requires_prompts_under_spb(tmp_path: Path) -> None:
    from spb.cli import cli

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        "support_harness: [pi_agent]\n"
        "tool_provider_metadata: {pi_agent: {tools: []}}\n",
        encoding="utf-8",
    )
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "old.md").write_text("Old prompt.\n", encoding="utf-8")

    result = CliRunner().invoke(cli, ["validate", "--project-root", str(tmp_path)])

    assert result.exit_code != 0
    assert ".spb/prompts/" in result.output


def test_render_rejects_a_prompt_outside_spb(tmp_path: Path) -> None:
    from spb.cli import cli

    runner = CliRunner()
    assert runner.invoke(cli, ["init", str(tmp_path)]).exit_code == 0
    (tmp_path / "prompts").mkdir()
    prompt_path = tmp_path / "prompts" / "coder.md"
    prompt_path.write_text("---\nname: Coder\nversion: 1.0.0\n---\nHello.\n")

    result = runner.invoke(
        cli,
        [
            "render",
            str(prompt_path),
            "--project-root",
            str(tmp_path),
            "--harness",
            "pi_agent",
        ],
    )

    assert result.exit_code != 0
    assert "Prompt must be under .spb/prompts/" in result.output
    assert not (tmp_path / "build").exists()


@pytest.mark.parametrize(
    "invalid_config",
    [
        "support-harness: [pi_agent]",
        "supportHarness: [pi_agent]",
        "support_harness: [pi-agent]",
        "support_harness: [piAgent]",
        "tool_provider_metadata: {pi-agent: {tools: []}}",
        "skill_providers: [{name: local, type: git, skill-root: skills}]",
    ],
)
def test_validate_rejects_non_snake_case_configuration(
    tmp_path: Path, invalid_config: str
) -> None:
    from spb.cli import cli

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        "version: 1\nsupport_harness: [pi_agent]\n"
        "tool_provider_metadata: {pi_agent: {tools: []}}\n"
        "skill_providers: []\n" + invalid_config + "\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["validate", "--project-root", str(tmp_path)])

    assert result.exit_code != 0
    assert "snake_case" in result.output


@pytest.mark.parametrize("name", ["projectName", "project-name"])
def test_validate_rejects_non_snake_case_prompt_variables(
    tmp_path: Path, name: str
) -> None:
    from spb.cli import cli

    runner = CliRunner()
    assert runner.invoke(cli, ["init", str(tmp_path)]).exit_code == 0
    prompt_path = tmp_path / ".spb" / "prompts" / "project-assistant.md"
    prompt_path.write_text(
        "---\nname: Assistant\nversion: 1.0.0\nvariables:\n"
        f"  {name}:\n    required: true\n---\nHello.\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli, ["validate", "--project-root", str(tmp_path)])

    assert result.exit_code != 0
    assert "snake_case" in result.output


def test_render_command_writes_a_harness_specific_artifact(tmp_path: Path) -> None:
    from spb.cli import cli

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        """\
version: 1
support_harness:
  - pi_agent
tool_provider_metadata:
  pi_agent:
    tools: []
skill_providers:
  - name: local
    type: local
    path: .spb/skills
""",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "skills").mkdir()
    (tmp_path / ".spb" / "skills" / "workflow.md").write_text("Follow the workflow.\n")
    (tmp_path / ".spb" / "prompts").mkdir()
    prompt_path = tmp_path / ".spb" / "prompts" / "coder.md"
    prompt_path.write_text(
        """\
---
name: Coder
version: 1.0.0
skills:
  - local/workflow
variables:
  project_name:
    required: true
---
You are a coding agent for {{{project_name}}}.
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        [
            "render",
            str(prompt_path),
            "--harness",
            "pi_agent",
            "--project-root",
            str(tmp_path),
            "--var",
            "project_name=acme=platform",
        ],
    )

    output_path = tmp_path / "build" / "pi_agent" / "coder.md"
    manifest_path = output_path.with_suffix(".manifest.yaml")
    assert result.exit_code == 0
    assert output_path.read_text(encoding="utf-8") == (
        "You are a coding agent for acme=platform.\n\nFollow the workflow.\n"
    )
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert manifest["name"] == "Coder"
    assert manifest["version"] == "1.0.0"
    assert len(manifest["rendered_sha256"]) == 64
    assert manifest["variables"] == {"project_name": "acme=platform"}
    assert manifest["skills"][0]["reference"] == "local/workflow"
    assert len(manifest["skills"][0]["sha256"]) == 64
    assert str(output_path) in result.output


def test_render_command_records_layout_in_manifest(tmp_path: Path) -> None:
    from spb.cli import cli

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        "version: 1\nsupport_harness:\n  - pi_agent\n"
        "tool_provider_metadata: {pi_agent: {tools: []}}\nskill_providers: []\n",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "layouts").mkdir()
    (tmp_path / ".spb" / "layouts" / "assistant.md").write_text(
        "<identity>\n{{{sections.identity}}}\n</identity>\n",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "prompts").mkdir()
    prompt_path = tmp_path / ".spb" / "prompts" / "assistant.md"
    prompt_path.write_text(
        "---\nname: Assistant\nversion: 1.0.0\n"
        "layout: .spb/layouts/assistant.md\n---\n<identity>\nYou help.\n</identity>\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        [
            "render",
            str(prompt_path),
            "--harness",
            "pi_agent",
            "--project-root",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    output_path = tmp_path / "build" / "pi_agent" / "assistant.md"
    assert (
        output_path.read_text(encoding="utf-8")
        == "<identity>\nYou help.\n</identity>\n"
    )
    manifest = yaml.safe_load(
        output_path.with_suffix(".manifest.yaml").read_text(encoding="utf-8")
    )
    assert manifest["layout"]["path"].endswith(".spb/layouts/assistant.md")
    assert len(manifest["layout"]["sha256"]) == 64


def test_render_rejects_a_local_provider_outside_spb(tmp_path: Path) -> None:
    from spb.cli import cli

    runner = CliRunner()
    assert runner.invoke(cli, ["init", str(tmp_path)]).exit_code == 0
    config_path = tmp_path / ".spb" / "config.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["skill_providers"][0]["path"] = "skills/local"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    prompt_path = tmp_path / ".spb" / "prompts" / "project-assistant.md"
    prompt_path.write_text(
        "---\nname: Assistant\nversion: 1.0.0\nskills: [local/example]\n---\nHello.\n",
        encoding="utf-8",
    )

    result = runner.invoke(cli, ["validate", "--project-root", str(tmp_path)])

    assert result.exit_code != 0
    assert "path must be under .spb/skills/" in result.output


def test_validate_rejects_a_prompt_without_a_semantic_version(tmp_path: Path) -> None:
    from spb.cli import cli

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        """\
version: 1
support_harness:
  - pi_agent
tool_provider_metadata:
  pi_agent:
    tools: []
skill_providers: []
""",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "prompts").mkdir()
    (tmp_path / ".spb" / "prompts" / "coder.md").write_text(
        """\
---
name: Coder
version: latest
skills: []
---
You are a coding agent.
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["validate", "--project-root", str(tmp_path)])

    assert result.exit_code != 0
    assert "must define a semantic version" in result.output


def test_validate_accepts_runtime_required_variables(tmp_path: Path) -> None:
    from spb.cli import cli

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        """\
version: 1
support_harness:
  - pi_agent
tool_provider_metadata:
  pi_agent:
    tools: []
skill_providers: []
""",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "prompts").mkdir()
    (tmp_path / ".spb" / "prompts" / "coder.md").write_text(
        """\
---
name: Coder
version: 1.0.0
skills: []
variables:
  project_name:
    required: true
---
You are assisting {{{project_name}}}.
""",
        encoding="utf-8",
    )

    result = CliRunner().invoke(cli, ["validate", "--project-root", str(tmp_path)])

    assert result.exit_code == 0
    assert "Validated 1 prompt(s)." in result.output


def test_render_rejects_changed_content_for_an_existing_release(tmp_path: Path) -> None:
    from spb.cli import cli

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        """\
version: 1
support_harness: [pi_agent]
tool_provider_metadata:
  pi_agent:
    tools: []
skill_providers: []
""",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "prompts").mkdir()
    prompt_path = tmp_path / ".spb" / "prompts" / "coder.md"
    prompt_path.write_text(
        "---\nname: Coder\nversion: 1.0.0\nskills: []\n---\nFirst release.\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    arguments = [
        "render",
        str(prompt_path),
        "--harness",
        "pi_agent",
        "--project-root",
        str(tmp_path),
    ]

    assert runner.invoke(cli, arguments).exit_code == 0
    prompt_path.write_text(
        "---\nname: Coder\nversion: 1.0.0\nskills: []\n---\nChanged release.\n",
        encoding="utf-8",
    )

    collision = runner.invoke(cli, arguments)
    replacement = runner.invoke(cli, [*arguments, "--replace-release"])

    assert collision.exit_code != 0
    assert "release collision" in collision.output
    assert replacement.exit_code == 0
    assert "Replacing release Coder@1.0.0" in replacement.output


def test_render_resolves_pinned_git_skill_and_writes_lockfile(tmp_path: Path) -> None:
    from spb.cli import cli

    repository = tmp_path / "skill-repository"
    (repository / "skills").mkdir(parents=True)
    (repository / "skills" / "typescript.md").write_text(
        "Use strict TypeScript.\n", encoding="utf-8"
    )
    _git(repository, "init", "-q")
    _git(repository, "config", "user.email", "tests@example.com")
    _git(repository, "config", "user.name", "Test User")
    _git(repository, "add", ".")
    _git(repository, "commit", "-qm", "Add skill")
    revision = _git(repository, "rev-parse", "HEAD").strip()

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        f"""\
version: 1
support_harness: [pi_agent]
tool_provider_metadata:
  pi_agent:
    tools: []
skill_providers:
  - name: team
    type: git
    gitrepo: {repository.as_uri()}
    revision: {revision}
    skill_root: skills
""",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "prompts").mkdir()
    prompt_path = tmp_path / ".spb" / "prompts" / "coder.md"
    prompt_path.write_text(
        "---\nname: Coder\nversion: 1.0.0\nskills: [team/typescript]\n"
        "---\nCode well.\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        [
            "render",
            str(prompt_path),
            "--harness",
            "pi_agent",
            "--project-root",
            str(tmp_path),
        ],
    )

    lockfile = yaml.safe_load(
        (tmp_path / ".spb" / "skills.lock.yaml").read_text(encoding="utf-8")
    )
    assert result.exit_code == 0
    assert "Use strict TypeScript." in (
        tmp_path / "build" / "pi_agent" / "coder.md"
    ).read_text(encoding="utf-8")
    assert lockfile["providers"]["team"]["revision"] == revision
    assert lockfile["providers"]["team"]["skills"][0]["reference"] == "team/typescript"


def test_render_with_none_compressor_writes_compressed_artifact(tmp_path: Path) -> None:
    from spb.cli import cli

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        """\
version: 1
support_harness: [pi_agent]
tool_provider_metadata:
  pi_agent:
    tools: []
skill_providers: []
""",
        encoding="utf-8",
    )
    (tmp_path / ".spb" / "prompts").mkdir()
    prompt_path = tmp_path / ".spb" / "prompts" / "coder.md"
    prompt_path.write_text(
        "---\nname: Coder\nversion: 1.0.0\nskills: []\n---\nCode well.\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        [
            "render",
            str(prompt_path),
            "--harness",
            "pi_agent",
            "--project-root",
            str(tmp_path),
            "--compress",
            "--compressor",
            "none",
        ],
    )

    output_path = tmp_path / "build" / "pi_agent" / "coder.md"
    compressed_path = output_path.with_suffix(".compressed.md")
    manifest = yaml.safe_load(
        output_path.with_suffix(".manifest.yaml").read_text(encoding="utf-8")
    )
    assert result.exit_code == 0
    assert compressed_path.read_text(encoding="utf-8") == output_path.read_text(
        encoding="utf-8"
    )
    assert manifest["compression"]["compressor"] == "none"
    assert len(manifest["compression"]["sha256"]) == 64


def test_link_creates_a_symlink_to_a_compiled_artifact(tmp_path: Path) -> None:
    from spb.cli import cli

    source = tmp_path / "build" / "pi_agent" / "coder.md"
    source.parent.mkdir(parents=True)
    source.write_text("Compiled prompt.\n", encoding="utf-8")
    destination = tmp_path / "consumer" / ".agent" / "system.md"

    result = CliRunner().invoke(cli, ["link", str(source), str(destination)])

    assert result.exit_code == 0
    assert destination.is_symlink()
    assert destination.resolve() == source.resolve()
    assert str(destination) in result.output


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=repository,
        check=True,
        text=True,
        capture_output=True,
    ).stdout


def test_fragment_render_manifest_records_source_digest(tmp_path: Path) -> None:
    import hashlib

    from spb.cli import cli

    (tmp_path / ".spb" / "prompts").mkdir(parents=True)
    (tmp_path / ".spb" / "config.yaml").write_text(
        "support_harness: [pi_agent]\n"
        "tool_provider_metadata: {pi_agent: {tools: []}}\n"
        "skill_providers: []\n",
        encoding="utf-8",
    )
    bundle = tmp_path / ".spb" / "fragments" / "identity"
    bundle.mkdir(parents=True)
    (bundle / "FRAGMENT.md").write_text("Hello.\n", encoding="utf-8")
    (tmp_path / ".spb" / "layouts").mkdir()
    (tmp_path / ".spb" / "layouts" / "one.md").write_text(
        "{{{fragments.identity}}}\n", encoding="utf-8"
    )
    prompt = tmp_path / ".spb" / "prompts" / "one.md"
    prompt.write_text(
        "---\nname: One\nversion: 1.0.0\n"
        "layout: .spb/layouts/one.md\n"
        "fragments: {identity: .spb/fragments/identity}\n---\n",
        encoding="utf-8",
    )
    args = [
        "render",
        str(prompt),
        "--harness",
        "pi_agent",
        "--project-root",
        str(tmp_path),
    ]
    result = CliRunner().invoke(cli, args)
    assert result.exit_code == 0, result.output
    manifest_path = tmp_path / "build" / "pi_agent" / "one.manifest.yaml"
    first = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    assert first["fragments"] == [
        {
            "alias": "identity",
            "path": str(bundle / "FRAGMENT.md"),
            "sha256": hashlib.sha256(b"Hello.\n").hexdigest(),
            "mode": "template",
        }
    ]
    (bundle / "FRAGMENT.md").write_text("Changed.\n", encoding="utf-8")
    collision = CliRunner().invoke(cli, args)
    assert collision.exit_code != 0
    assert "release collision" in collision.output


def test_render_rejects_project_variable_override(tmp_path: Path) -> None:
    from spb.cli import cli

    runner = CliRunner()
    assert runner.invoke(cli, ["init", str(tmp_path)]).exit_code == 0
    result = runner.invoke(
        cli,
        [
            "render",
            str(tmp_path / ".spb" / "prompts" / "project-assistant.md"),
            "--harness",
            "pi_agent",
            "--project-root",
            str(tmp_path),
            "--var",
            "project=other",
        ],
    )
    assert result.exit_code != 0
    assert "Reserved --var name: project" in result.output


def test_render_compresses_only_declared_fragment_aliases(tmp_path: Path) -> None:
    from spb.cli import cli

    runner = CliRunner()
    assert runner.invoke(cli, ["init", str(tmp_path)]).exit_code == 0
    prompt = tmp_path / ".spb" / "prompts" / "project-assistant.md"
    prompt.write_text(
        prompt.read_text(encoding="utf-8").replace(
            "skills: []", "compressible_fragments: [instructions]\nskills: []"
        ),
        encoding="utf-8",
    )
    result = runner.invoke(
        cli,
        [
            "render",
            str(prompt),
            "--harness",
            "pi_agent",
            "--project-root",
            str(tmp_path),
            "--compress",
            "--compressor",
            "none",
        ],
    )
    assert result.exit_code == 0, result.output
    output = tmp_path / "build" / "pi_agent" / "project-assistant.md"
    assert output.with_suffix(".compressed.md").read_text() == output.read_text()
    manifest = yaml.safe_load(output.with_suffix(".manifest.yaml").read_text())
    assert manifest["compression"]["settings"]["scope"] == "selected_fragments"
    assert [
        entry["alias"] for entry in manifest["compression"]["settings"]["fragments"]
    ] == ["instructions"]


def test_render_rejects_fragment_compression_without_opt_in(tmp_path: Path) -> None:
    from spb.cli import cli

    runner = CliRunner()
    assert runner.invoke(cli, ["init", str(tmp_path)]).exit_code == 0
    result = runner.invoke(
        cli,
        [
            "render",
            str(tmp_path / ".spb" / "prompts" / "project-assistant.md"),
            "--harness",
            "pi_agent",
            "--project-root",
            str(tmp_path),
            "--compress",
            "--compressor",
            "none",
        ],
    )
    assert result.exit_code != 0
    assert "compressible_fragments" in result.output
    assert not (tmp_path / "build" / "pi_agent" / "project-assistant.md").exists()
