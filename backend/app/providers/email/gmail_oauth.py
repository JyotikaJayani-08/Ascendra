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
        """Send email via Gmail API with robust token refresh handling.

        Flow:
          1. If no access_token but refresh_token exists → refresh first
          2. Try sending
          3. If 401 → refresh token and retry once
          4. self.access_token always reflects the latest token for caller to persist
        """
        # ── Step 1: Proactively refresh if we have no access token ────
        if not self.access_token and self.refresh_token:
            refreshed = await self.refresh_access_token()
            if not refreshed:
                return SendResult(
                    success=False,
                    error="Gmail OAuth: No access token and token refresh failed. "
                          "Please re-authenticate Gmail in Profile → Email Settings.",
                )

        # ── Step 2: Attempt send ──────────────────────────────────────
        provider = GmailProvider(access_token=self.access_token)
        result = await provider.send(message)

        if result.success:
            return result

        # ── Step 3: If expired token (401), refresh and retry once ────
        is_token_error = "401" in str(result.error) or "invalid_token" in str(result.error).lower()

        if is_token_error and self.refresh_token:
            logger.info("Gmail OAuth token expired. Refreshing and retrying...")
            new_token = await self.refresh_access_token()
            if new_token:
                provider = GmailProvider(access_token=new_token)
                result = await provider.send(message)
                if result.success:
                    logger.info("Gmail send succeeded after token refresh.")
                    return result

            # Refresh failed — give a clear actionable error
            if not new_token:
                return SendResult(
                    success=False,
                    error="Gmail OAuth: Access token expired and refresh failed. "
                          "Please re-authenticate Gmail in Profile → Email Settings.",
                )

        return result
