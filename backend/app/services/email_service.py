import smtplib
from email.mime.text import MIMEText

from app.core.config import settings


def send_email(receiver: str, otp: str):

    msg = MIMEText(
        f"Your OTP is {otp}"
    )

    msg["Subject"] = "StackPilot Verification"
    msg["From"] = settings.EMAIL_ADDRESS
    msg["To"] = receiver

    server = smtplib.SMTP(
        "smtp.gmail.com",
        587
    )

    server.starttls()

    server.login(
        settings.EMAIL_ADDRESS,
        settings.EMAIL_PASSWORD
    )

    server.send_message(msg)

    server.quit()

def frontend_base_url() -> str:
    """First configured frontend origin (set FRONTEND_ORIGINS on the server), else local dev."""
    origins = [o.strip().rstrip("/") for o in settings.FRONTEND_ORIGINS.split(",") if o.strip()]
    return origins[0] if origins else "http://localhost:5173"


def send_invite_email(receiver: str, board_name: str, role: str, inviter_name: str | None, token: str):
    """Best-effort invitation email (runs as a background task; never raises)."""
    import logging

    try:
        link = f"{frontend_base_url()}/invite/{token}"
        who = inviter_name or "A StackPilot user"
        msg = MIMEText(
            f"{who} invited you to the project \"{board_name}\" as {role.replace('_', ' ')}.\n\n"
            f"Open this link to review and accept the invitation:\n{link}\n\n"
            f"Sign in (or create an account) with {receiver}. The invitation only works for that email address "
            f"and expires in 7 days."
        )
        msg["Subject"] = f"You were invited to {board_name} on StackPilot"
        msg["From"] = settings.EMAIL_ADDRESS
        msg["To"] = receiver
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
        server.starttls()
        server.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
    except Exception:
        logging.getLogger("stackpilot").exception("Invite email failed (invitation is still saved)")
