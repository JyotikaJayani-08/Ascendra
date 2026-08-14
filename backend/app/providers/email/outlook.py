"""
Ascendra — Outlook Graph API Provider.

Sends emails via the Microsoft Graph API using OAuth2 access tokens.
"""

import logging

import httpx

from app.providers.email.base import EmailMessage, EmailProvider, SendResult

logger = logging.getLogger("ascendra.providers.email.outlook")


class OutlookProvider(EmailProvider):
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.api_url = "https://graph.microsoft.com/v1.0/me/sendMail"

    @property
    def provider_name(self) -> str:
        return "outlook_graph"

    async def send(self, message: EmailMessage) -> SendResult:
        """Send an email using Microsoft Graph API."""
        if not self.access_token:
            return SendResult(success=False, error="Missing access_token for Outlook Provider.")

        # Construct Graph API JSON payload
        payload = {
            "message": {
                "subject": message.subject,
                "body": {
                    "contentType": "HTML",
                    "content": message.body_html
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": message.to_email
                        }
                    }
                ]
            },
            "saveToSentItems": "true"
        }
        
        # Add reply-to if specified
        if message.reply_to:
            payload["message"]["replyTo"] = [
                {
                    "emailAddress": {
                        "address": message.reply_to
                    }
                }
            ]

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, json=payload, headers=headers)
                
                # Graph API returns 202 Accepted for successful sending
                if response.status_code in (200, 202):
                    logger.info(f"Outlook email sent successfully to {message.to_email}")
                    # Graph API does not return a message ID directly in the 202 response
                    return SendResult(success=True, message_id="graph-api-sent")
                else:
                    error_msg = response.text
                    try:
                        error_data = response.json()
                        error_msg = error_data.get("error", {}).get("message", response.text)
                    except Exception:
                        pass
                    logger.error(f"Outlook send failed with status {response.status_code}: {error_msg}")
                    return SendResult(success=False, error=error_msg)
        except Exception as e:
            logger.error(f"Outlook send encountered an exception: {e}")
            return SendResult(success=False, error=str(e))
