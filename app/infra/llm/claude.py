"""Anthropic Claude wrappers.

stream_claude: yields SSE-formatted data lines for streaming endpoints.
call_claude: blocking call returning full text; wrap in asyncio.to_thread().
"""
from __future__ import annotations

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
