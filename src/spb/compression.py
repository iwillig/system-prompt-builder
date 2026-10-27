"""Optional prompt-compression adapters."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from spb.rendering import RenderedPrompt, compose_fragment_content


@dataclass(frozen=True)
class CompressionResult:
    """The output and provenance of one compression operation."""

    content: str
    compressor: str
    settings: dict[str, Any]


def compress_prompt(
    content: str, compressor: str, *, rate: float = 0.5
) -> CompressionResult:
    """Compress content with a named optional compressor at a target rate."""
    if not 0 < rate <= 1:
        raise ValueError("Compression rate must be between 0 and 1")
    if compressor == "none":
        return CompressionResult(
            content=content, compressor="none", settings={"rate": rate}
        )
    if compressor == "llmlingua":
        return _compress_with_llmlingua(content, rate)
    raise ValueError(f"Unsupported compressor: {compressor}")


def compress_rendered_prompt(
    prompt: RenderedPrompt, compressor: str, *, rate: float = 0.5
) -> CompressionResult:
    """Compress selected fragments, or the whole body for legacy prompts."""
    if not prompt.fragments:
        return compress_prompt(prompt.content, compressor, rate=rate)
    if not prompt.compressible_fragments:
        raise ValueError(
            "Fragment prompt requires compressible_fragments for compression"
        )

    values = prompt.rendered_fragments.copy()
    details: list[dict[str, Any]] = []
    for alias in prompt.compressible_fragments:
        original = values[alias]
        compressed = compress_prompt(original, compressor, rate=rate)
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


def _compress_with_llmlingua(content: str, rate: float) -> CompressionResult:
    try:
        compressor = _llmlingua_compressor()
    except ImportError as error:
        raise ValueError(
            "LLMLingua is not installed; install the llmlingua optional dependency"
        ) from error

    output = compressor.compress_prompt(
        [content], instruction="", question="", rate=rate
    )
    compressed = output.get("compressed_prompt")
    if not isinstance(compressed, str):
        raise ValueError("LLMLingua did not return a compressed prompt")
    return CompressionResult(
        content=compressed,
        compressor="llmlingua",
        settings={"rate": rate},
    )


@lru_cache(maxsize=1)
def _llmlingua_compressor() -> Any:
    """Load the LLMLingua compressor once per process.

    The default LLMLingua-2 model runs on CPU. Override the model or device
    with the ``SPB_LLMLINGUA_MODEL`` and ``SPB_LLMLINGUA_DEVICE``
    environment variables.
    """
    import os

    from llmlingua import PromptCompressor  # type: ignore[import-untyped]

    return PromptCompressor(
        model_name=os.environ.get(
            "SPB_LLMLINGUA_MODEL",
            "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
        ),
        use_llmlingua2=True,
        device_map=os.environ.get("SPB_LLMLINGUA_DEVICE", "cpu"),
    )
