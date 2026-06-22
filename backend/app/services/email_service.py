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