"""Langfuse client — prompt management + LLM observability.

Unlike the other infra/ modules (claude.py, voyage.py construct a fresh vendor
client per call), Langfuse's SDK is meant to be a long-lived singleton: it
batches and flushes events on a background thread. This module lazily
constructs that singleton on first use, from Vault-sourced keys passed in by
the caller (same calling convention as every other infra module here).

Every public function is failure-isolated. Langfuse being down, misconfigured,
or erroring must never break the app — this is best-effort observability, not
a Vault/DB-style hard dependency (Constitution Principle II does not apply
here). On any error this module logs a warning and degrades:
  - get_prompt() returns the caller's `fallback` string.
  - trace() yields a no-op handle.
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

from langfuse import Langfuse

from app.infra.vault import AppSecrets

logger = logging.getLogger(__name__)

# Not a secret — internal service URL, same treatment as GUARDRAILS_URL.
_LANGFUSE_HOST = os.environ.get("LANGFUSE_HOST", "http://langfuse:3000")

_client: Langfuse | None = None
_client_unavailable = False


def _get_client(secrets: AppSecrets) -> Langfuse | None:
    """Return the lazily-constructed singleton, or None if unconfigured.

    A missing public/secret key is treated as "Langfuse intentionally
    disabled" and cached so later calls don't re-check empty strings. A
    network-down Langfuse is NOT cached here — that surfaces per-call in
    get_prompt()/trace() and self-heals once Langfuse comes back, without
    requiring an app restart.
    """
    global _client, _client_unavailable
    if _client is not None:
        return _client
    if _client_unavailable:
        return None
    if not secrets.langfuse_public_key or not secrets.langfuse_secret_key:
        logger.warning("Langfuse keys not configured in Vault — observability disabled.")
        _client_unavailable = True
        return None
    try:
        _client = Langfuse(
            public_key=secrets.langfuse_public_key,
            secret_key=secrets.langfuse_secret_key,
            host=_LANGFUSE_HOST,
        )
    except Exception as exc:
        logger.warning("Failed to construct Langfuse client: %s", exc)
        _client_unavailable = True
        return None
    return _client


def get_prompt(
    secrets: AppSecrets,
    name: str,
    label: str = "production",
    fallback: str | None = None,
) -> str:
    """Fetch a prompt's text by (name, label). Falls back to `fallback` on any error.

    `fallback` is an in-code literal (the value that used to be hardcoded) —
    this codebase's prompts are Python constants/functions, not files, so
    there is no fallback_path to read.
    """
    client = _get_client(secrets)
    if client is None:
        return fallback or ""
    try:
        # Bounded timeout/retries: an unreachable Langfuse must fail over to
        # the fallback in ~seconds, not the SDK's default multi-retry backoff
        # (observed ~8s) — every chat/exam/grading call routes through here.
        prompt = client.get_prompt(name, label=label, fallback=fallback, max_retries=1, fetch_timeout_seconds=3)
        return prompt.prompt
    except Exception as exc:
        logger.warning("Langfuse get_prompt(%r, label=%r) failed: %s — using fallback.", name, label, exc)
        return fallback or ""


class TraceHandle:
    """Mutable scratch space set by the caller before the `trace()` block exits.

    Latency is derived by Langfuse automatically from generation start/end —
    callers don't need to time anything themselves.
    """

    def __init__(self) -> None:
        self.input: Any = None
        self.output: Any = None
        self.model: str | None = None
        self.usage: dict[str, Any] | None = None

    def set_usage(self, input_tokens: int | None, output_tokens: int | None) -> None:
        if input_tokens is None and output_tokens is None:
            return
        self.usage = {
            "unit": "TOKENS",
            "input": input_tokens,
            "output": output_tokens,
            "total": (input_tokens or 0) + (output_tokens or 0),
        }


@contextmanager
def trace(
    secrets: AppSecrets,
    name: str,
    user_id: str | None = None,
    session_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[TraceHandle]:
    """Wrap a single Claude call. Set `.input` / `.output` / `.model` (or call
    `.set_usage(...)`) on the yielded handle before the block exits.

    Never raises — on any Langfuse error this yields a no-op handle, so call
    sites never need an `if traced:` branch around their Claude call.
    """
    client = _get_client(secrets)
    if client is None:
        yield TraceHandle()
        return

    generation = None
    try:
        trace_obj = client.trace(name=name, user_id=user_id, session_id=session_id, metadata=metadata)
        generation = trace_obj.generation(name=name, metadata=metadata)
    except Exception as exc:
        logger.warning("Langfuse trace(%r) setup failed: %s", name, exc)
        yield TraceHandle()
        return

    handle = TraceHandle()
    try:
        yield handle
    finally:
        try:
            generation.end(
                input=handle.input,
                output=handle.output,
                model=handle.model,
                usage=handle.usage,
            )
        except Exception as exc:
            logger.warning("Langfuse trace(%r) finalize failed: %s", name, exc)
