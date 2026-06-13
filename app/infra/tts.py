"""ElevenLabs text-to-speech synthesis via httpx (async)."""
import httpx

from app.domain.exceptions import TTSServiceUnavailable

_VOICE_ID = "JBFqnCBsd6RMkjVDRZzb"  # ElevenLabs "George" voice
_MODEL_ID = "eleven_flash_v2_5"
_API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"


async def synthesize(text: str, api_key: str) -> bytes:
    """Call ElevenLabs TTS and return raw mp3 bytes.

    Raises TTSServiceUnavailable on any HTTP or network error.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{_API_BASE}/{_VOICE_ID}",
                headers={
                    "xi-api-key": api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={"text": text, "model_id": _MODEL_ID},
            )
            response.raise_for_status()
            return response.content
    except httpx.HTTPStatusError as exc:
        raise TTSServiceUnavailable(
            f"ElevenLabs returned {exc.response.status_code}"
        ) from exc
    except httpx.RequestError as exc:
        raise TTSServiceUnavailable(f"ElevenLabs unreachable: {exc}") from exc
