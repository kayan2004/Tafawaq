"""Redis client helpers.

All keys carry explicit TTLs (Constitution Principle III).
TTL constants are defined once here and used at every write site.
"""
import json
from typing import Any

from redis.asyncio import Redis

# Active exam content + generated answer key.
# Justification: matches the 3-hour real exam duration; sessions self-clean after expiry.
SESSION_TTL = 10_800  # 3 hours in seconds

# Consecutive off-topic message counter per conversation.
# Justification: co-expires with the session; the counter is meaningless after the session ends.
GUARDRAILS_TTL = 10_800  # 3 hours in seconds


# ── Session helpers ───────────────────────────────────────────────────────────

async def set_session(redis: Redis, session_id: str, data: dict[str, Any]) -> None:
    await redis.set(f"session:{session_id}", json.dumps(data), ex=SESSION_TTL)


# ── Guardrails helpers ────────────────────────────────────────────────────────

async def get_guardrails_counter(redis: Redis, session_id: str) -> int:
    raw = await redis.get(f"guardrails:{session_id}")
    return int(raw) if raw is not None else 0


async def set_guardrails_counter(redis: Redis, session_id: str, value: int) -> None:
    await redis.set(f"guardrails:{session_id}", value, ex=GUARDRAILS_TTL)


async def increment_guardrails_counter(redis: Redis, session_id: str) -> int:
    key = f"guardrails:{session_id}"
    new_value: int = await redis.incr(key)
    # Reset TTL on every increment so the counter co-expires with an active session.
    await redis.expire(key, GUARDRAILS_TTL)
    return new_value
