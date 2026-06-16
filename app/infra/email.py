"""Resend transactional email — used for password-reset notifications.

Email delivery is best-effort: a missing API key or a Resend failure logs a
warning and returns rather than raising, so a flaky/unconfigured email
provider can never crash the forgot-password request.
"""
import logging

import httpx

logger = logging.getLogger(__name__)

_RESEND_API_BASE = "https://api.resend.com/emails"


async def send_email(*, to: str, subject: str, html: str, api_key: str, from_email: str) -> None:
    if not api_key:
        logger.warning("RESEND_API_KEY not configured — skipping email to %s", to)
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                _RESEND_API_BASE,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"from": from_email, "to": [to], "subject": subject, "html": html},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Failed to send email to %s via Resend: %s", to, exc)


async def send_reset_password_email(*, to: str, reset_url: str, api_key: str, from_email: str) -> None:
    html = (
        "<p>We received a request to reset your Tafawwaq password.</p>"
        f'<p><a href="{reset_url}">Click here to reset your password</a></p>'
        "<p>This link expires in 1 hour. If you didn't request this, you can safely ignore this email.</p>"
    )
    await send_email(
        to=to,
        subject="Reset your Tafawwaq password",
        html=html,
        api_key=api_key,
        from_email=from_email,
    )
