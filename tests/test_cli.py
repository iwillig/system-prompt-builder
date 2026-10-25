import subprocess
from pathlib import Path

import yaml
from click.testing import CliRunner


def test_render_command_writes_a_harness_specific_artifact(tmp_path: Path) -> None:
    from spb.cli import cli

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        """\
version: 1
support-harness:
  - pi-agent
tool-provider-metadata:
  pi-agent:
    tools: []
skill-providers:
  - name: local
    type: local
    path: skills
""",
        encoding="utf-8",
    )
    (tmp_path / "skills").mkdir()
    (tmp_path / "skills" / "workflow.md").write_text("Follow the workflow.\n")
    (tmp_path / "prompts").mkdir()
    prompt_path = tmp_path / "prompts" / "coder.md"
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
            "pi-agent",
            "--project-root",
            str(tmp_path),
            "--var",
            "project_name=acme=platform",
        ],
    )

    output_path = tmp_path / "build" / "pi-agent" / "coder.md"
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


def test_validate_rejects_a_prompt_without_a_semantic_version(tmp_path: Path) -> None:
    from spb.cli import cli

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        """\
version: 1
support-harness:
  - pi-agent
tool-provider-metadata:
  pi-agent:
    tools: []
skill-providers: []
""",
        encoding="utf-8",
    )
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "coder.md").write_text(
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
support-harness:
  - pi-agent
tool-provider-metadata:
  pi-agent:
    tools: []
skill-providers: []
""",
        encoding="utf-8",
    )
    (tmp_path / "prompts").mkdir()
    (tmp_path / "prompts" / "coder.md").write_text(
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
support-harness: [pi-agent]
tool-provider-metadata:
  pi-agent:
    tools: []
skill-providers: []
""",
        encoding="utf-8",
    )
    (tmp_path / "prompts").mkdir()
    prompt_path = tmp_path / "prompts" / "coder.md"
    prompt_path.write_text(
        "---\nname: Coder\nversion: 1.0.0\nskills: []\n---\nFirst release.\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    arguments = [
        "render",
        str(prompt_path),
        "--harness",
        "pi-agent",
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
support-harness: [pi-agent]
tool-provider-metadata:
  pi-agent:
    tools: []
skill-providers:
  - name: team
    type: git
    gitrepo: {repository.as_uri()}
    revision: {revision}
    skill-root: skills
""",
        encoding="utf-8",
    )
    (tmp_path / "prompts").mkdir()
    prompt_path = tmp_path / "prompts" / "coder.md"
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
            "pi-agent",
            "--project-root",
            str(tmp_path),
        ],
    )

    lockfile = yaml.safe_load(
        (tmp_path / ".spb" / "skills.lock.yaml").read_text(encoding="utf-8")
    )
    assert result.exit_code == 0
    assert "Use strict TypeScript." in (
        tmp_path / "build" / "pi-agent" / "coder.md"
    ).read_text(encoding="utf-8")
    assert lockfile["providers"]["team"]["revision"] == revision
    assert lockfile["providers"]["team"]["skills"][0]["reference"] == "team/typescript"


def test_render_with_none_compressor_writes_compressed_artifact(tmp_path: Path) -> None:
    from spb.cli import cli

    (tmp_path / ".spb").mkdir()
    (tmp_path / ".spb" / "config.yaml").write_text(
        """\
version: 1
support-harness: [pi-agent]
tool-provider-metadata:
  pi-agent:
    tools: []
skill-providers: []
""",
        encoding="utf-8",
    )
    (tmp_path / "prompts").mkdir()
    prompt_path = tmp_path / "prompts" / "coder.md"
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
            "pi-agent",
            "--project-root",
            str(tmp_path),
            "--compress",
            "--compressor",
            "none",
        ],
    )

    output_path = tmp_path / "build" / "pi-agent" / "coder.md"
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

    source = tmp_path / "build" / "pi-agent" / "coder.md"
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
