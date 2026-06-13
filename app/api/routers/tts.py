"""POST /tts — proxy spoken-English text to ElevenLabs TTS (key stays server-side)."""
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.dependencies import get_secrets
from app.infra.auth import current_active_user
from app.infra.vault import AppSecrets
from app.repositories.orm import UserORM
from app.services import tts_service

router = APIRouter(prefix="/tts", tags=["tts"])


class TTSRequest(BaseModel):
    text: str


@router.post("", response_class=Response)
async def synthesize_speech(
    body: TTSRequest,
    secrets: AppSecrets = Depends(get_secrets),
    _user: UserORM = Depends(current_active_user),
) -> Response:
    audio = await tts_service.get_or_synthesize(body.text, secrets)
    return Response(content=audio, media_type="audio/mpeg")
