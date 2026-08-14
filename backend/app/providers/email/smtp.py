"""
Ascendra — SMTP Email Provider.

Provider-independent SMTP implementation supporting both
global (system fallback) and per-user credentials.
"""

import logging
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.config import settings
from app.providers.email.base import EmailMessage, EmailProvider, SendResult

logger = logging.getLogger("ascendra.providers.email.smtp")


@dataclass
class SMTPCredentials:
    """Encapsulated SMTP connection credentials."""
    host: str
    port: int
    username: str
    password: str


class SMTPProvider(EmailProvider):
    """
    SMTP email provider with support for per-user credentials.

    Follows doc/09 §110 provider architecture:
    - Business modules never call providers directly.
    - Each provider implements the same interface.
    """

    @property
    def provider_name(self) -> str:
        return "smtp"

    async def send(
        self,
        message: EmailMessage,
        credentials: SMTPCredentials | None = None,
    ) -> SendResult:
        """
        Send an email via SMTP.

        If per-user credentials are provided, use those.
        Otherwise, fall back to global .env SMTP settings.
        """
        creds = credentials or self._get_global_credentials()
        if not creds:
            logger.warning("SMTP not configured — email not sent")
            return SendResult(success=False, error="SMTP not configured")

        mime_msg = self._build_mime_message(message, creds.username)
        return await self._connect_and_send(mime_msg, creds)

    # ── Private Helpers ───────────────────────────────────────

    @staticmethod
    def _get_global_credentials() -> SMTPCredentials | None:
        """Retrieve system-wide SMTP credentials from .env as fallback."""
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            return None
        return SMTPCredentials(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USERNAME,
            password=settings.SMTP_PASSWORD,
        )

    @staticmethod
    def _build_mime_message(message: EmailMessage, sender_address: str) -> MIMEMultipart:
        """Construct the MIME message with proper headers and optional attachments."""
        if message.attachments:
            msg = MIMEMultipart("mixed")
            body_container = MIMEMultipart("alternative")
            if message.body_text:
                body_container.attach(MIMEText(message.body_text, "plain"))
            if message.body_html:
                body_container.attach(MIMEText(message.body_html, "html"))
            msg.attach(body_container)

            from email.mime.application import MIMEApplication
            from email.mime.text import MIMEText as TextPart
            for att in message.attachments:
                filename = att.get("filename", "attachment")
                content = att.get("content", b"")
                content_type = att.get("content_type", "application/pdf")
                
                if isinstance(content, str):
                    content = content.encode("utf-8")

                if "pdf" in content_type:
                    part = MIMEApplication(content, _subtype="pdf")
                elif "text" in content_type or filename.endswith((".txt", ".md")):
                    part = TextPart(content.decode("utf-8", errors="ignore"), "plain")
                else:
                    part = MIMEApplication(content)

                part.add_header("Content-Disposition", "attachment", filename=filename)
                msg.attach(part)
        else:
            msg = MIMEMultipart("alternative")
            if message.body_text:
                msg.attach(MIMEText(message.body_text, "plain"))
            if message.body_html:
                msg.attach(MIMEText(message.body_html, "html"))

        # From header: use display name if available, always send from SMTP account
        sender_name = message.from_name or "Candidate"
        msg["From"] = f"{sender_name} <{sender_address}>"
        msg["To"] = message.to_email
        msg["Subject"] = message.subject

        # Reply-To: prefer explicit reply_to, then from_email, then omit
        reply_to = message.reply_to or message.from_email
        if reply_to and reply_to != sender_address:
            msg["Reply-To"] = reply_to

        return msg

    @staticmethod
    async def _connect_and_send(
        mime_msg: MIMEMultipart, creds: SMTPCredentials
    ) -> SendResult:
        """Open SMTP connection, authenticate, and send the message."""
        try:
            await aiosmtplib.send(
                mime_msg,
                hostname=creds.host,
                port=creds.port,
                username=creds.username,
                password=creds.password,
                start_tls=True,
            )
            recipient = mime_msg["To"]
            logger.info(f"Email sent to {recipient}")
            return SendResult(success=True, message_id=mime_msg.get("Message-ID"))
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            return SendResult(success=False, error=str(e))


smtp_provider = SMTPProvider()
