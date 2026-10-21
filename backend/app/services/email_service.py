import os
import logging
import httpx

from app.core.config import settings

logger = logging.getLogger("stackpilot")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"


def _send_via_brevo(receiver: str, subject: str, text: str) -> None:
    """Send a plain-text email through Brevo's HTTPS API (port 443, not blocked by Railway)."""
    api_key = os.getenv("BREVO_API_KEY")
    if not api_key:
        raise RuntimeError("BREVO_API_KEY is not configured")

    # Must be a sender you verified in Brevo
    sender_email = os.getenv("MAIL_FROM") or settings.EMAIL_ADDRESS
    sender_name = os.getenv("MAIL_FROM_NAME", "StackPilot")

    resp = httpx.post(
        BREVO_URL,
        json={
            "sender": {"name": sender_name, "email": sender_email},
            "to": [{"email": receiver}],
            "subject": subject,
            "textContent": text,
        },
        headers={"api-key": api_key, "accept": "application/json"},
        timeout=15,
    )

    if resp.status_code >= 400:
        logger.error("Brevo error %s: %s", resp.status_code, resp.text)
        raise RuntimeError(f"Brevo rejected the email ({resp.status_code})")


def send_email(receiver: str, otp: str):
    _send_via_brevo(
        receiver,
        "StackPilot Verification",
        f"Your OTP is {otp}",
    )


def frontend_base_url() -> str:
    """First configured frontend origin (set FRONTEND_ORIGINS on the server), else local dev."""
    origins = [o.strip().rstrip("/") for o in settings.FRONTEND_ORIGINS.split(",") if o.strip()]
    return origins[0] if origins else "http://localhost:5173"


def send_invite_email(receiver: str, board_name: str, role: str, inviter_name: str | None, token: str):
    """Best-effort invitation email (runs as a background task; never raises)."""
    try:
        link = f"{frontend_base_url()}/invite/{token}"
        who = inviter_name or "A StackPilot user"
        text = (
            f"{who} invited you to the project \"{board_name}\" as {role.replace('_', ' ')}.\n\n"
            f"Open this link to review and accept the invitation:\n{link}\n\n"
            f"Sign in (or create an account) with {receiver}. The invitation only works for that email address "
            f"and expires in 7 days."
        )
        _send_via_brevo(receiver, f"You were invited to {board_name} on StackPilot", text)
    except Exception:
        logger.exception("Invite email failed (invitation is still saved)")