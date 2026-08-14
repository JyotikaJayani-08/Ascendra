"""
Ascendra — Outlook Microsoft Graph OAuth2 Provider & Token Refresher.

Wraps Microsoft Graph API provider with automatic OAuth2 token decryption
and token refreshing.
"""

import logging
import httpx

from app.core.security import decrypt_credential
from app.providers.email.base import EmailMessage, EmailProvider, SendResult
from app.providers.email.outlook import OutlookProvider

logger = logging.getLogger("ascendra.providers.email.outlook_oauth")


class OutlookOAuthProvider(EmailProvider):
    """
    Outlook Microsoft Graph OAuth 2.0 Provider with auto token refresh.
    """

    def __init__(
        self,
        access_token: str,
        refresh_token: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        tenant_id: str = "common",
    ):
        self.access_token = decrypt_credential(access_token) if access_token else ""
        self.refresh_token = decrypt_credential(refresh_token) if refresh_token else ""
        self.client_id = decrypt_credential(client_id) if client_id else ""
        self.client_secret = decrypt_credential(client_secret) if client_secret else ""
        self.token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    @property
    def provider_name(self) -> str:
        return "outlook_oauth"

    async def refresh_access_token(self) -> str | None:
        """Attempt to obtain a fresh access token using refresh_token."""
        if not (self.refresh_token and self.client_id and self.client_secret):
            logger.warning("Missing required OAuth refresh credentials for Outlook Graph API.")
            return None

        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
            "scope": "https://graph.microsoft.com/Mail.Send offline_access",
        }

        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(self.token_url, data=payload)
                if res.status_code == 200:
                    data = res.json()
                    new_token = data.get("access_token")
                    if new_token:
                        self.access_token = new_token
                        logger.info("Successfully refreshed Outlook Graph OAuth access token.")
                        return new_token
                else:
                    logger.error(f"Outlook token refresh failed ({res.status_code}): {res.text}")
        except Exception as err:
            logger.error(f"Outlook token refresh exception: {err}")

        return None

    async def send(self, message: EmailMessage) -> SendResult:
        """Send email via Microsoft Graph API, attempting token refresh if 401 is encountered."""
        if not self.access_token and self.refresh_token:
            await self.refresh_access_token()

        provider = OutlookProvider(access_token=self.access_token)
        result = await provider.send(message)

        # If unauthorized/expired token, attempt single refresh retry
        if not result.success and ("401" in str(result.error) or "Access token has expired" in str(result.error)):
            logger.info("Outlook OAuth token invalid or expired. Attempting token refresh...")
            new_token = await self.refresh_access_token()
            if new_token:
                provider = OutlookProvider(access_token=new_token)
                result = await provider.send(message)

        return result
