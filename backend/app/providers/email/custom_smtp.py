"""
Ascendra — Custom Dynamic SMTP Email Provider.

Supports candidate outreach sending via Yahoo, Zoho, Rediff, Fastmail, or any Custom Business Domain SMTP.
"""

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.providers.email.base import EmailMessage, EmailProvider, SendResult

logger = logging.getLogger("ascendra.providers.email.custom_smtp")


class CustomSMTPProvider(EmailProvider):

    def __init__(self, host: str, port: int, username: str, password: str, use_tls: bool = True):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls

    @property
    def provider_name(self) -> str:
        return "custom_smtp"

    async def send(self, message: EmailMessage) -> SendResult:
        """Send an email via candidate's dynamic SMTP server."""
        if not self.host or not self.username or not self.password:
            return SendResult(success=False, error="Custom SMTP credentials incomplete.")

        msg = MIMEMultipart("alternative")
        msg["From"] = self.username
        msg["To"] = message.to_email
        msg["Subject"] = message.subject

        if message.body_text:
            msg.attach(MIMEText(message.body_text, "plain"))
        msg.attach(MIMEText(message.body_html, "html"))

        if message.reply_to:
            msg["Reply-To"] = message.reply_to

        try:
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                start_tls=self.use_tls,
            )
            logger.info(f"Custom SMTP email sent to {message.to_email} via {self.host}")
            return SendResult(success=True, message_id=msg.get("Message-ID"))
        except Exception as e:
            logger.error(f"Custom SMTP send failed via {self.host}: {e}")
            return SendResult(success=False, error=str(e))
