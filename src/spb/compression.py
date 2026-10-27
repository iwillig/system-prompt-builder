"""Optional prompt-compression adapters."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from spb.rendering import RenderedPrompt, compose_fragment_content


@dataclass(frozen=True)
class CompressionResult:
    """The output and provenance of one compression operation."""

    content: str
    compressor: str
    settings: dict[str, Any]


def compress_prompt(content: str, compressor: str) -> CompressionResult:
    """Compress content with a named optional compressor."""
    if compressor == "none":
        return CompressionResult(content=content, compressor="none", settings={})
    if compressor == "llmlingua":
        return _compress_with_llmlingua(content)
    raise ValueError(f"Unsupported compressor: {compressor}")


def compress_rendered_prompt(
    prompt: RenderedPrompt, compressor: str
) -> CompressionResult:
    """Compress selected fragments, or the whole body for legacy prompts."""
    if not prompt.fragments:
        return compress_prompt(prompt.content, compressor)
    if not prompt.compressible_fragments:
        raise ValueError(
            "Fragment prompt requires compressible_fragments for compression"
        )

    values = prompt.rendered_fragments.copy()
    details: list[dict[str, Any]] = []
    for alias in prompt.compressible_fragments:
        original = values[alias]
        compressed = compress_prompt(original, compressor)
        if not compressed.content.strip():
            raise ValueError(f"Compressor returned empty fragment: {alias}")
        values[alias] = compressed.content
        details.append(
            {
                "alias": alias,
                "input_sha256": hashlib.sha256(original.encode("utf-8")).hexdigest(),
                "output_sha256": hashlib.sha256(
                    compressed.content.encode("utf-8")
                ).hexdigest(),
                "settings": compressed.settings,
            }
        )
    return CompressionResult(
        content=compose_fragment_content(prompt, values),
        compressor=compressor,
        settings={"scope": "selected_fragments", "fragments": details},
    )


def _compress_with_llmlingua(content: str) -> CompressionResult:
    try:
        from llmlingua import PromptCompressor  # type: ignore[import-not-found]
    except ImportError as error:
        raise ValueError(
            "LLMLingua is not installed; install the llmlingua optional dependency"
        ) from error

    target_token = 200
    output = PromptCompressor().compress_prompt(
        content, instruction="", question="", target_token=target_token
    )
    compressed = output.get("compressed_prompt")
    if not isinstance(compressed, str):
        raise ValueError("LLMLingua did not return a compressed prompt")
    return CompressionResult(
        content=compressed,
        compressor="llmlingua",
        settings={"target_token": target_token},
    )
