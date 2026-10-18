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

def send_invite_email(receiver: str, board_name: str, role: str, inviter_name: str | None):
    """Best-effort invitation email (runs as a background task; never raises)."""
    import logging

    try:
        origins = [o.strip().rstrip("/") for o in settings.FRONTEND_ORIGINS.split(",") if o.strip()]
        link = f"\n\nOpen StackPilot: {origins[0]}/boards" if origins else ""
        who = inviter_name or "A StackPilot user"
        msg = MIMEText(
            f"{who} invited you to the project \"{board_name}\" as {role.replace('_', ' ')}.\n"
            f"Log in with this email address and accept the invitation on your Boards page."
            f"{link}"
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