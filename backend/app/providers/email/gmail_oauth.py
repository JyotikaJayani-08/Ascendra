"""
Ascendra — Gmail OAuth2 Provider & Token Refresher.

Wraps Gmail REST API provider with automatic OAuth2 token decryption
and token refreshing.
"""

import logging
import time
import httpx

from app.core.security import decrypt_credential, encrypt_credential
from app.providers.email.base import EmailMessage, EmailProvider, SendResult
from app.providers.email.gmail import GmailProvider

logger = logging.getLogger("ascendra.providers.email.gmail_oauth")


class GmailOAuthProvider(EmailProvider):
    """
    Gmail OAuth 2.0 Provider with auto token refresh.
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.access_token = decrypt_credential(access_token) if access_token else ""
        self.refresh_token = decrypt_credential(refresh_token) if refresh_token else ""
        self.client_id = decrypt_credential(client_id) if client_id else ""
        self.client_secret = decrypt_credential(client_secret) if client_secret else ""
        self.token_url = "https://oauth2.googleapis.com/token"

    @property
    def provider_name(self) -> str:
        return "gmail_oauth"

    async def refresh_access_token(self) -> str | None:
        """Attempt to obtain a fresh access token using refresh_token."""
        if not (self.refresh_token and self.client_id and self.client_secret):
            logger.warning("Missing required OAuth refresh credentials for Gmail.")
            return None

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(self.token_url, data=payload)
                if res.status_code == 200:
                    data = res.json()
                    new_token = data.get("access_token")
                    if new_token:
                        self.access_token = new_token
                        logger.info("Successfully refreshed Gmail OAuth access token.")
                        return new_token
                else:
                    logger.error(f"Gmail token refresh failed ({res.status_code}): {res.text}")
        except Exception as err:
            logger.error(f"Gmail token refresh exception: {err}")

        return None

    async def send(self, message: EmailMessage) -> SendResult:
        """Send email via Gmail API, attempting token refresh if 401 is encountered."""
        if not self.access_token and self.refresh_token:
            await self.refresh_access_token()

        provider = GmailProvider(access_token=self.access_token)
        result = await provider.send(message)

        # If unauthorized/expired token, attempt single refresh retry
        if not result.success and ("401" in str(result.error) or "invalid_token" in str(result.error).lower()):
            logger.info("Gmail OAuth token invalid or expired. Attempting token refresh...")
            new_token = await self.refresh_access_token()
            if new_token:
                provider = GmailProvider(access_token=new_token)
                result = await provider.send(message)

        return result
