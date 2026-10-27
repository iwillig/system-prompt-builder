from pathlib import Path

import pytest

from spb.compression import CompressionResult, compress_rendered_prompt
from spb.initialization import initialize_project
from spb.rendering import render_prompt, validate_project


def _project(tmp_path: Path, *, eligible: str | None = "details") -> Path:
    project = initialize_project(tmp_path, harness="pi_agent")
    layout = project.layout
    layout.write_text(
        "<identity>\n{{{fragments.identity}}}\n</identity>\n\n"
        "<details>\n{{{fragments.details}}}\n</details>\n",
        encoding="utf-8",
    )
    identity = tmp_path / ".spb" / "fragments" / "identity"
    identity.mkdir()
    (identity / "FRAGMENT.md").write_text("Never change this.\n", encoding="utf-8")
    details = tmp_path / ".spb" / "fragments" / "details"
    details.mkdir()
    (details / "FRAGMENT.md").write_text(
        "Many details for {{project}}.\n", encoding="utf-8"
    )
    source = (
        "---\nname: Assistant\nversion: 1.0.0\n"
        "layout: .spb/layouts/project-assistant.md\n"
        "fragments:\n"
        "  identity: .spb/fragments/identity\n"
        "  details: .spb/fragments/details\n"
    )
    if eligible is not None:
        source += f"compressible_fragments: [{eligible}]\n"
    project.prompt.write_text(source + "---\n", encoding="utf-8")
    return project.prompt


def test_only_opted_in_fragment_is_compressed(tmp_path: Path, monkeypatch) -> None:
    import spb.compression as compression

    prompt_path = _project(tmp_path)
    rendered = render_prompt(tmp_path, prompt_path, harness="pi_agent")
    seen: list[str] = []

    def fake_compress(content: str, compressor: str) -> CompressionResult:
        seen.append(content)
        assert compressor == "llmlingua"
        return CompressionResult("Short details.", compressor, {"target_token": 200})

    monkeypatch.setattr(compression, "compress_prompt", fake_compress)
    compressed = compress_rendered_prompt(rendered, "llmlingua")

    assert seen == ["Many details for " + tmp_path.name + "."]
    assert compressed.content == (
        "<identity>\nNever change this.\n</identity>\n\n"
        "<details>\nShort details.\n</details>\n"
    )
    assert rendered.content.startswith("<identity>\nNever change this.")
    assert compressed.settings["fragments"][0]["alias"] == "details"
    assert compressed.settings["fragments"][0]["input_sha256"]
    assert compressed.settings["fragments"][0]["output_sha256"]


def test_fragment_compression_requires_opt_in(tmp_path: Path) -> None:
    prompt_path = _project(tmp_path, eligible=None)
    rendered = render_prompt(tmp_path, prompt_path, harness="pi_agent")
    with pytest.raises(ValueError, match="compressible_fragments"):
        compress_rendered_prompt(rendered, "none")


@pytest.mark.parametrize("eligible", ["unknown", "identity, identity", ""])
def test_invalid_compressible_aliases_fail_static_validation(
    tmp_path: Path, eligible: str
) -> None:
    _project(tmp_path, eligible=eligible)
    with pytest.raises(ValueError, match="compressible_fragments"):
        validate_project(tmp_path)


def test_legacy_compression_policy_is_rejected(tmp_path: Path) -> None:
    project = initialize_project(tmp_path, harness="pi_agent")
    project.prompt.write_text(
        "---\nname: Assistant\nversion: 1.0.0\n"
        "compressible_fragments: [instructions]\n---\nHello.\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="compressible_fragments"):
        validate_project(tmp_path)


def test_empty_compressed_fragment_is_rejected(tmp_path: Path, monkeypatch) -> None:
    import spb.compression as compression

    rendered = render_prompt(tmp_path, _project(tmp_path), harness="pi_agent")
    monkeypatch.setattr(
        compression,
        "compress_prompt",
        lambda _content, _compressor: CompressionResult("", "llmlingua", {}),
    )
    with pytest.raises(ValueError, match="empty fragment: details"):
        compress_rendered_prompt(rendered, "llmlingua")


def test_appended_skill_text_remains_unchanged(tmp_path: Path, monkeypatch) -> None:
    import spb.compression as compression

    prompt_path = _project(tmp_path)
    skill_path = tmp_path / ".spb" / "skills" / "local" / "guard.md"
    skill_path.write_text("Do not remove this skill.\n", encoding="utf-8")
    prompt_path.write_text(
        prompt_path.read_text(encoding="utf-8").replace(
            "compressible_fragments: [details]",
            "compressible_fragments: [details]\nskills: [local/guard]",
        ),
        encoding="utf-8",
    )
    rendered = render_prompt(tmp_path, prompt_path, harness="pi_agent")
    monkeypatch.setattr(
        compression,
        "compress_prompt",
        lambda _content, compressor: CompressionResult("Short.", compressor, {}),
    )
    result = compress_rendered_prompt(rendered, "llmlingua")
    assert result.content.endswith("\n\nDo not remove this skill.\n")
    assert "Never change this." in result.content
