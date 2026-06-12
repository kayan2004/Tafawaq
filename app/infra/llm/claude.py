"""Anthropic Claude wrappers.

stream_claude: yields SSE-formatted data lines for streaming endpoints.
call_claude: blocking call returning full text; wrap in asyncio.to_thread().
call_claude_vision: blocking vision call (image or PDF); wrap in asyncio.to_thread().
"""
from __future__ import annotations

import base64
import json
from typing import AsyncGenerator

import anthropic

from app.domain.exceptions import AIServiceUnavailable


async def stream_claude(
    messages: list[dict],
    system: str,
    api_key: str,
    tools: list[dict] | None = None,
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    client = anthropic.AsyncAnthropic(api_key=api_key)
    kwargs: dict = dict(
        model="claude-sonnet-4-5",
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    if tools:
        kwargs["tools"] = tools

    try:
        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield f"data: {json.dumps({'event': 'token', 'text': text})}\n\n"

            if tools:
                final = await stream.get_final_message()
                if final.stop_reason == "tool_use":
                    for block in final.content:
                        if block.type == "tool_use":
                            yield f"data: {json.dumps({'event': 'tool_use', 'tool_use_id': block.id, 'name': block.name, 'input': block.input})}\n\n"
    except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
        raise AIServiceUnavailable(str(exc)) from exc

    yield "data: [DONE]\n\n"


def call_claude(
    messages: list[dict],
    system: str,
    api_key: str,
    max_tokens: int = 2048,
) -> str:
    """Synchronous (blocking) call — use asyncio.to_thread() from async context."""
    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
    except anthropic.APIStatusError as exc:
        raise AIServiceUnavailable(str(exc)) from exc
    return response.content[0].text


_VISION_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_VISION_PDF_TYPE = "application/pdf"


def call_claude_vision(
    file_bytes: bytes,
    mime_type: str,
    prompt: str,
    api_key: str,
    max_tokens: int = 4096,
    prefill: str | None = None,
) -> str:
    """Sync vision call accepting an image or PDF — use asyncio.to_thread() from async context.

    Pass prefill="{" to force Claude to start its response with that string,
    guaranteeing JSON output without markdown wrappers.
    """
    data = base64.standard_b64encode(file_bytes).decode("utf-8")
    client = anthropic.Anthropic(api_key=api_key)

    if mime_type == _VISION_PDF_TYPE:
        content = [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}},
            {"type": "text", "text": prompt},
        ]
        extra = {"extra_headers": {"anthropic-beta": "pdfs-2024-09-25"}}
    elif mime_type in _VISION_IMAGE_TYPES:
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": data}},
            {"type": "text", "text": prompt},
        ]
        extra = {}
    else:
        from app.domain.exceptions import ExtractionFailed
        raise ExtractionFailed(f"Unsupported file type '{mime_type}'. Upload a JPEG, PNG, WEBP, or PDF.")

    messages: list[dict] = [{"role": "user", "content": content}]
    if prefill:
        messages.append({"role": "assistant", "content": prefill})

    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=max_tokens,
            messages=messages,
            **extra,
        )
    except anthropic.APIStatusError as exc:
        raise AIServiceUnavailable(str(exc)) from exc

    if not response.content or response.content[0].type != "text":
        from app.domain.exceptions import ExtractionFailed
        raise ExtractionFailed(
            f"Claude returned no text. stop_reason={response.stop_reason!r} "
            f"content_types={[b.type for b in response.content]!r}"
        )
    if response.stop_reason == "max_tokens":
        from app.domain.exceptions import ExtractionFailed
        raise ExtractionFailed(
            "Extraction response was cut off (max_tokens reached). "
            "Try a shorter document or fewer exercises."
        )
    text = response.content[0].text
    return (prefill + text) if prefill else text
