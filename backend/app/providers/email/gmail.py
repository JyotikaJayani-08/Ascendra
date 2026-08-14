"""
Ascendra — Gmail API Provider.

Sends emails via the Gmail REST API using OAuth2 access tokens.
"""

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import httpx

from app.providers.email.base import EmailMessage, EmailProvider, SendResult

logger = logging.getLogger("ascendra.providers.email.gmail")


class GmailProvider(EmailProvider):
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.api_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"

    @property
    def provider_name(self) -> str:
        return "gmail_api"

    async def send(self, message: EmailMessage) -> SendResult:
        """Send an email using Gmail REST API."""
        if not self.access_token:
            return SendResult(success=False, error="Missing access_token for Gmail Provider.")

        # Construct MIME Message — use "mixed" when attachments are present
        if message.attachments:
            msg = MIMEMultipart("mixed")
            body_container = MIMEMultipart("alternative")
            if message.body_text:
                body_container.attach(MIMEText(message.body_text, "plain"))
            if message.body_html:
                body_container.attach(MIMEText(message.body_html, "html"))
            msg.attach(body_container)

            from email.mime.application import MIMEApplication
            for att in message.attachments:
                filename = att.get("filename", "attachment")
                content = att.get("content", b"")
                content_type = att.get("content_type", "application/pdf")

                if isinstance(content, str):
                    content = content.encode("utf-8")

                if "pdf" in content_type:
                    part = MIMEApplication(content, _subtype="pdf")
                elif "text" in content_type or filename.endswith((".txt", ".md")):
                    part = MIMEText(content.decode("utf-8", errors="ignore"), "plain")
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

        msg["To"] = message.to_email
        msg["Subject"] = message.subject

        if message.reply_to:
            msg["Reply-To"] = message.reply_to

        # Gmail requires web-safe base64 encoding without padding or newlines
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        payload = {"raw": raw_message}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    message_id = data.get("id")
                    logger.info(f"Gmail sent successfully to {message.to_email}, Message-ID: {message_id}")
                    return SendResult(success=True, message_id=message_id)
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text)
                    except Exception:
                        pass
                    logger.error(f"Gmail send failed with status {response.status_code}: {error_msg}")
                    return SendResult(success=False, error=f"{response.status_code}: {error_msg}")
        except Exception as e:
            logger.error(f"Gmail send encountered an exception: {e}")
            return SendResult(success=False, error=str(e))
