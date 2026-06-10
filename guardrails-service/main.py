"""NeMo Guardrails classifier service.

Exposes POST /check — returns {"off_topic": bool}.
The main API calls this service; all counter/tier/blocking logic stays in
the main app's guardrails_service.py.

Classification uses a custom NeMo action (check_math_topic) that calls
Claude Haiku with a single prompt — one LLM call per classified message.

Secrets: ANTHROPIC_API_KEY injected via Docker Compose env (deviation from
Vault-first principle noted — this service has no runtime Vault dependency).
"""
from __future__ import annotations

import asyncio
import os
from typing import Optional

import anthropic
from fastapi import FastAPI, HTTPException
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.actions import action
from pydantic import BaseModel

app = FastAPI(title="Lebanese Math Guardrails", version="1.0.0")

_rails: LLMRails | None = None

_OFF_TOPIC_SENTINEL = "OFF_TOPIC"

from prompts.classification import CLASSIFICATION_PROMPT as _CLASSIFICATION_PROMPT


@action(is_system_action=True)
async def check_math_topic(context: Optional[dict] = None) -> bool:
    """Return True if the message is about Lebanese GS Math; False otherwise."""
    message = (context or {}).get("user_message", "")
    if not message.strip():
        return True  # empty / very short — allow

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = await asyncio.to_thread(
        client.messages.create,
        model="claude-haiku-4-5-20251001",
        max_tokens=3,
        messages=[{
            "role": "user",
            "content": _CLASSIFICATION_PROMPT.format(message=message),
        }],
    )
    answer = resp.content[0].text.strip().lower()
    print(f"[check_math_topic] message={message[:60]!r} answer={answer!r}", flush=True)
    return answer.startswith("yes")


@app.on_event("startup")
async def startup() -> None:
    global _rails
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set — guardrails service cannot start.")
    config = RailsConfig.from_path("./config")
    _rails = LLMRails(config)
    _rails.register_action(check_math_topic, name="check_math_topic")
    print("[startup] NeMo Guardrails initialised.", flush=True)


class CheckRequest(BaseModel):
    message: str


class CheckResponse(BaseModel):
    off_topic: bool


@app.post("/check", response_model=CheckResponse)
async def check(req: CheckRequest) -> CheckResponse:
    if _rails is None:
        raise HTTPException(status_code=503, detail="Rails not initialised yet.")
    try:
        result = await _rails.generate_async(
            messages=[{"role": "user", "content": req.message}]
        )
    except Exception as exc:
        print(f"[check] NeMo generate failed: {exc}", flush=True)
        # Fail open — on error treat as on-topic.
        return CheckResponse(off_topic=False)

    # NeMo 0.22+ returns a dict with "content" key; older returns str.
    if isinstance(result, dict):
        text = result.get("content", "")
    else:
        text = str(result)

    off_topic = text.strip() == _OFF_TOPIC_SENTINEL
    print(f"[check] text={text[:80]!r} off_topic={off_topic}", flush=True)
    return CheckResponse(off_topic=off_topic)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "rails_ready": _rails is not None}
