"""Optional prompt-compression adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
