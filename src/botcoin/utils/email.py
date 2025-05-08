"""This module contains utility functions for sending emails."""

import os
from email.message import EmailMessage

import aiosmtplib
from dotenv import load_dotenv

load_dotenv()
EMAIL_USER = os.getenv("NOTIFY_EMAIL_ADDRESS")
EMAIL_PASS = os.getenv("NOTIFY_EMAIL_PASSWORD")


async def send_email(subject: str, body: str) -> None:
    """send email using aiosmtplib"""
    msg = EmailMessage()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER
    msg["Subject"] = f"[Botcoin]: {subject}"
    msg.set_content(body)

    await aiosmtplib.send(
        msg,
        hostname="smtp.gmail.com",
        port=465,
        username=EMAIL_USER,
        password=EMAIL_PASS,
        use_tls=True,
    )
