"""NeMo Guardrails classifier service.

Exposes:
  POST /check         — input classification (chat message / exam-generation brief)
  POST /check-output   — output classification (generated chat reply / exam content)

Two separate LLMRails instances, each with one custom action + one flow, so input
and output classification never cross-fire on the same call. All counter/tier/
blocking/logging logic stays in the main app's app/services/guardrails_service.py.

Secrets: ANTHROPIC_API_KEY injected via Docker Compose env (deviation from
Vault-first principle noted — this service has no runtime Vault dependency).
"""
from __future__ import annotations

import asyncio
import os

import anthropic
from fastapi import FastAPI, HTTPException
from nemoguardrails import LLMRails, RailsConfig
from nemoguardrails.actions import action
from pydantic import BaseModel

from prompts.classification import CLASSIFICATION_PROMPT, OUTPUT_CLASSIFICATION_PROMPT
from verdict import parse_input_verdict, parse_output_verdict

app = FastAPI(title="Lebanese Math Guardrails", version="2.0.0")

_input_rails: LLMRails | None = None
_output_rails: LLMRails | None = None

_INPUT_YAML = """
models:
  - type: main
    engine: anthropic
    model: claude-haiku-4-5-20251001
rails:
  input:
    flows:
      - check input safety
"""

_OUTPUT_YAML = """
models:
  - type: main
    engine: anthropic
    model: claude-haiku-4-5-20251001
rails:
  input:
    flows:
      - check output safety
"""

_INPUT_COLANG = """
define flow check input safety
  $verdict = execute classify_input_action
  stop
"""

_OUTPUT_COLANG = """
define flow check output safety
  $verdict = execute classify_output_action
  stop
"""


def _call_haiku_sync(prompt: str) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


@action(is_system_action=True)
async def classify_input_action(context: dict | None = None) -> dict:
    message = (context or {}).get("user_message", "")
    raw = await asyncio.to_thread(_call_haiku_sync, CLASSIFICATION_PROMPT.format(message=message))
    verdict = parse_input_verdict(raw)
    return {"category": verdict.category, "score": verdict.score, "reason": verdict.reason}


@action(is_system_action=True)
async def classify_output_action(context: dict | None = None) -> dict:
    content = (context or {}).get("user_message", "")
    raw = await asyncio.to_thread(_call_haiku_sync, OUTPUT_CLASSIFICATION_PROMPT.format(content=content))
    verdict = parse_output_verdict(raw)
    return {"flagged": verdict.flagged, "score": verdict.score, "reason": verdict.reason}


@app.on_event("startup")
async def startup() -> None:
    global _input_rails, _output_rails
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set — guardrails service cannot start.")

    input_config = RailsConfig.from_content(colang_content=_INPUT_COLANG, yaml_content=_INPUT_YAML)
    _input_rails = LLMRails(input_config)
    _input_rails.register_action(classify_input_action, name="classify_input_action")

    output_config = RailsConfig.from_content(colang_content=_OUTPUT_COLANG, yaml_content=_OUTPUT_YAML)
    _output_rails = LLMRails(output_config)
    _output_rails.register_action(classify_output_action, name="classify_output_action")

    print("[startup] NeMo Guardrails initialised (input + output rails).", flush=True)


class CheckRequest(BaseModel):
    message: str


class CheckResponse(BaseModel):
    category: str | None
    score: float
    reason: str


class CheckOutputResponse(BaseModel):
    flagged: bool
    score: float
    reason: str


@app.post("/check", response_model=CheckResponse)
async def check(req: CheckRequest) -> CheckResponse:
    if _input_rails is None:
        raise HTTPException(status_code=503, detail="Rails not initialised yet.")
    try:
        result = await _input_rails.generate_async(
            messages=[{"role": "user", "content": req.message}],
            options={"output_vars": ["verdict"]},
        )
    except Exception as exc:
        print(f"[check] NeMo generate failed: {exc}", flush=True)
        return CheckResponse(category=None, score=0.0, reason="classifier error — failed open")
    verdict = (result.output_data or {}).get("verdict") or {}
    return CheckResponse(
        category=verdict.get("category"),
        score=float(verdict.get("score", 0.0)),
        reason=str(verdict.get("reason", "")),
    )


@app.post("/check-output", response_model=CheckOutputResponse)
async def check_output(req: CheckRequest) -> CheckOutputResponse:
    if _output_rails is None:
        raise HTTPException(status_code=503, detail="Rails not initialised yet.")
    try:
        result = await _output_rails.generate_async(
            messages=[{"role": "user", "content": req.message}],
            options={"output_vars": ["verdict"]},
        )
    except Exception as exc:
        print(f"[check-output] NeMo generate failed: {exc}", flush=True)
        return CheckOutputResponse(flagged=False, score=0.0, reason="classifier error — failed open")
    verdict = (result.output_data or {}).get("verdict") or {}
    return CheckOutputResponse(
        flagged=bool(verdict.get("flagged", False)),
        score=float(verdict.get("score", 0.0)),
        reason=str(verdict.get("reason", "")),
    )


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "input_rails_ready": _input_rails is not None,
        "output_rails_ready": _output_rails is not None,
    }
