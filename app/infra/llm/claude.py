"""Anthropic Claude wrappers.

stream_claude: yields SSE-formatted data lines for streaming endpoints.
call_claude: blocking call returning full text; wrap in asyncio.to_thread().
call_claude_vision: blocking vision call (image or PDF); wrap in asyncio.to_thread().

Every call is wrapped in a Langfuse trace (input/output/model/tokens). Tracing
is best-effort — see app/infra/langfuse_client.py — and never affects the
Claude call itself or its error handling.
"""
from __future__ import annotations

import base64
import json
from typing import AsyncGenerator, Any

import anthropic

from app.domain.exceptions import AIServiceUnavailable
from app.infra import langfuse_client
from app.infra.vault import AppSecrets

_MODEL = "claude-sonnet-4-5"


async def stream_claude(
    messages: list[dict],
    system: str,
    api_key: str,
    secrets: AppSecrets,
    tools: list[dict] | None = None,
    max_tokens: int = 4096,
    *,
    trace_name: str = "stream_claude",
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AsyncGenerator[str, None]:
    client = anthropic.AsyncAnthropic(api_key=api_key)
    kwargs: dict = dict(
        model=_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
    )
    if tools:
        kwargs["tools"] = tools

    with langfuse_client.trace(secrets, trace_name, user_id=user_id, session_id=session_id, metadata=metadata) as t:
        t.input = messages
        t.model = _MODEL
        full_text = ""
        try:
            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    full_text += text
                    yield f"data: {json.dumps({'event': 'token', 'text': text})}\n\n"

                # Always fetch the final message (previously only when tools
                # were passed) so usage/model are available for every call —
                # this does not change which SSE events are emitted.
                final = await stream.get_final_message()
                if tools and final.stop_reason == "tool_use":
                    for block in final.content:
                        if block.type == "tool_use":
                            yield f"data: {json.dumps({'event': 'tool_use', 'tool_use_id': block.id, 'name': block.name, 'input': block.input})}\n\n"

                t.output = full_text
                t.model = final.model
                t.set_usage(final.usage.input_tokens, final.usage.output_tokens)
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
            t.output = f"ERROR: {exc}"
            raise AIServiceUnavailable(str(exc)) from exc

    yield "data: [DONE]\n\n"


def call_claude(
    messages: list[dict],
    system: str,
    api_key: str,
    secrets: AppSecrets,
    max_tokens: int = 2048,
    *,
    trace_name: str = "call_claude",
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    """Synchronous (blocking) call — use asyncio.to_thread() from async context."""
    client = anthropic.Anthropic(api_key=api_key)
    with langfuse_client.trace(secrets, trace_name, user_id=user_id, session_id=session_id, metadata=metadata) as t:
        t.input = messages
        t.model = _MODEL
        try:
            response = client.messages.create(
                model=_MODEL,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
            )
        except anthropic.APIStatusError as exc:
            t.output = f"ERROR: {exc}"
            raise AIServiceUnavailable(str(exc)) from exc
        text = response.content[0].text
        t.output = text
        t.set_usage(response.usage.input_tokens, response.usage.output_tokens)
    return text


_VISION_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_VISION_PDF_TYPE = "application/pdf"


def call_claude_vision(
    file_bytes: bytes,
    mime_type: str,
    prompt: str,
    api_key: str,
    secrets: AppSecrets,
    max_tokens: int = 4096,
    prefill: str | None = None,
    *,
    trace_name: str = "call_claude_vision",
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
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

    with langfuse_client.trace(secrets, trace_name, user_id=user_id, session_id=session_id, metadata=metadata) as t:
        # Don't log the base64 image/PDF payload — just the text prompt.
        t.input = prompt
        t.model = _MODEL
        try:
            response = client.messages.create(
                model=_MODEL,
                max_tokens=max_tokens,
                messages=messages,
                **extra,
            )
        except anthropic.APIStatusError as exc:
            t.output = f"ERROR: {exc}"
            raise AIServiceUnavailable(str(exc)) from exc

        if not response.content or response.content[0].type != "text":
            from app.domain.exceptions import ExtractionFailed
            t.output = f"ERROR: no text content, stop_reason={response.stop_reason!r}"
            raise ExtractionFailed(
                f"Claude returned no text. stop_reason={response.stop_reason!r} "
                f"content_types={[b.type for b in response.content]!r}"
            )
        if response.stop_reason == "max_tokens":
            from app.domain.exceptions import ExtractionFailed
            t.output = "ERROR: max_tokens reached"
            raise ExtractionFailed(
                "Extraction response was cut off (max_tokens reached). "
                "Try a shorter document or fewer exercises."
            )
        text = response.content[0].text
        result = (prefill + text) if prefill else text
        t.output = result
        t.set_usage(response.usage.input_tokens, response.usage.output_tokens)
    return result
