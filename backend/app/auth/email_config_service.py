"""
Ascendra — User Email Config Service.

Per-user SMTP credential CRUD with test-send verification.
Encapsulates all DB access and provider interaction behind a clean interface.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import UserEmailConfig, EmailProviderType
from app.core.exceptions import NotFound, ValidationError

logger = logging.getLogger("ascendra.email_config")


class EmailConfigService:
    """Service for managing per-user email provider configurations."""

    # ── Public Interface ──────────────────────────────────────

    async def create_config(
        self,
        db: AsyncSession,
        user_id: str,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        display_name: str | None = None,
        provider_type: str = "SMTP",
        oauth_access_token: str | None = None,
        oauth_refresh_token: str | None = None,
        oauth_client_id: str | None = None,
        oauth_client_secret: str | None = None,
    ) -> UserEmailConfig:
        """Create or replace a user's email configuration."""
        from app.core.security import encrypt_credential, decrypt_credential

        encrypted_pwd = encrypt_credential(smtp_password) if smtp_password else ""
        encrypted_access = encrypt_credential(oauth_access_token) if oauth_access_token else None
        encrypted_refresh = encrypt_credential(oauth_refresh_token) if oauth_refresh_token else None
        encrypted_secret = encrypt_credential(oauth_client_secret) if oauth_client_secret else None

        enum_provider = EmailProviderType.SMTP
        if provider_type == "GMAIL_OAUTH":
            enum_provider = EmailProviderType.GMAIL_OAUTH
        elif provider_type == "OUTLOOK_OAUTH":
            enum_provider = EmailProviderType.OUTLOOK_OAUTH

        # Enforce one config per user for MVP (replace if exists)
        existing = await self._get_default_config(db, user_id)
        if existing:
            existing.provider_type = enum_provider
            existing.smtp_host = smtp_host
            existing.smtp_port = smtp_port
            existing.smtp_username = smtp_username
            # Only overwrite password if user provided a real new one
            if smtp_password and smtp_password not in ("", "••••••••"):
                existing.smtp_password = encrypted_pwd
                existing.is_verified = False  # Reset verification on credential change
            existing.display_name = display_name
            if oauth_access_token:
                existing.oauth_access_token = encrypted_access
            if oauth_refresh_token:
                existing.oauth_refresh_token = encrypted_refresh
            if oauth_client_id:
                existing.oauth_client_id = oauth_client_id
            if oauth_client_secret:
                existing.oauth_client_secret = encrypted_secret
            await db.commit()
            await db.refresh(existing)
            logger.info(f"Email config updated for user {user_id[:8]}")
            return existing

        config = UserEmailConfig(
            user_id=user_id,
            provider_type=enum_provider,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_username=smtp_username,
            smtp_password=encrypted_pwd,
            display_name=display_name,
            oauth_access_token=encrypted_access,
            oauth_refresh_token=encrypted_refresh,
            oauth_client_id=oauth_client_id,
            oauth_client_secret=encrypted_secret,
            is_default=True,
            is_verified=False,
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
        logger.info(f"Email config created for user {user_id[:8]}")
        return config

    async def create_gmail_oauth_config(
        self,
        db: AsyncSession,
        user_id: str,
        gmail_address: str,
        display_name: str,
        access_token: str,
        refresh_token: str,
        client_id: str,
        client_secret: str,
    ) -> UserEmailConfig:
        """
        Create or update a Gmail OAuth email configuration.

        Called after the Google OAuth callback successfully exchanges
        an authorization code for tokens. Auto-marks as verified since
        OAuth grants are inherently valid.
        """
        from app.core.security import encrypt_credential

        encrypted_access = encrypt_credential(access_token)
        encrypted_refresh = encrypt_credential(refresh_token) if refresh_token else None
        encrypted_secret = encrypt_credential(client_secret) if client_secret else None

        existing = await self._get_default_config(db, user_id)
        if existing:
            existing.provider_type = EmailProviderType.GMAIL_OAUTH
            existing.smtp_host = "gmail.googleapis.com"
            existing.smtp_port = 0  # Not used for OAuth
            existing.smtp_username = gmail_address
            existing.smtp_password = ""  # Not used for OAuth
            existing.display_name = display_name or gmail_address.split("@")[0]
            existing.oauth_access_token = encrypted_access
            existing.oauth_refresh_token = encrypted_refresh
            existing.oauth_client_id = client_id
            existing.oauth_client_secret = encrypted_secret
            existing.is_verified = True  # OAuth is inherently verified
            await db.commit()
            await db.refresh(existing)
            logger.info(f"Gmail OAuth config updated for user {user_id[:8]} ({gmail_address})")
            return existing

        config = UserEmailConfig(
            user_id=user_id,
            provider_type=EmailProviderType.GMAIL_OAUTH,
            smtp_host="gmail.googleapis.com",
            smtp_port=0,
            smtp_username=gmail_address,
            smtp_password="",
            display_name=display_name or gmail_address.split("@")[0],
            oauth_access_token=encrypted_access,
            oauth_refresh_token=encrypted_refresh,
            oauth_client_id=client_id,
            oauth_client_secret=encrypted_secret,
            is_default=True,
            is_verified=True,  # OAuth is inherently verified
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
        logger.info(f"Gmail OAuth config created for user {user_id[:8]} ({gmail_address})")
        return config

    async def get_config(self, db: AsyncSession, user_id: str) -> UserEmailConfig | None:
        """Retrieve the user's default email config (None if not configured)."""
        return await self._get_default_config(db, user_id)

    async def delete_config(self, db: AsyncSession, user_id: str) -> None:
        """Remove the user's email provider configuration."""
        config = await self._get_default_config(db, user_id)
        if not config:
            raise NotFound("EmailConfig")
        await db.delete(config)
        await db.commit()
        logger.info(f"Email config deleted for user {user_id[:8]}")

    async def test_config(
        self,
        db: AsyncSession,
        user_id: str,
        recipient_email: str | None = None,
    ) -> tuple[bool, str]:
        """
        Send a test email using the user's config to verify it works.

        Returns (success, message) tuple.
        Supports both SMTP and Gmail OAuth providers.
        """
        config = await self._get_default_config(db, user_id)
        if not config:
            raise NotFound("EmailConfig")

        target = recipient_email or config.smtp_username

        # Route to appropriate test method based on provider type
        if config.provider_type == EmailProviderType.GMAIL_OAUTH:
            success, message = await self._send_test_email_gmail_oauth(config, target, db=db)
        else:
            success, message = await self._send_test_email(config, target)

        if success:
            config.is_verified = True
            await db.commit()

        return success, message

    # ── Private Helpers ───────────────────────────────────────

    async def _get_default_config(
        self, db: AsyncSession, user_id: str
    ) -> UserEmailConfig | None:
        """Fetch the user's default email configuration."""
        result = await db.execute(
            select(UserEmailConfig).where(
                UserEmailConfig.user_id == user_id,
                UserEmailConfig.is_default == True,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def _send_test_email(config: UserEmailConfig, recipient: str) -> tuple[bool, str]:
        """Attempt to send a branded test email via the user's SMTP credentials."""
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText
        import aiosmtplib
        from app.core.security import decrypt_credential

        display = config.display_name or config.smtp_username.split("@")[0]

        msg = MIMEMultipart("alternative")
        msg["From"] = f"{display} <{config.smtp_username}>"
        msg["To"] = recipient
        msg["Subject"] = "Ascendra — SMTP Configuration Verified ✅"

        text_content = (
            "Ascendra — SMTP Configuration Verified\n\n"
            "If you received this email, your custom email connection is working correctly!\n\n"
            f"Configured Address: {config.smtp_username}\n"
            f"Host: {config.smtp_host}:{config.smtp_port}\n"
        )

        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4fdf8; margin: 0; padding: 32px 16px; }}
    .card {{ max-width: 520px; margin: 0 auto; background: #ffffff; border: 1px solid #d1fae5; border-radius: 16px; padding: 32px; box-shadow: 0 4px 16px rgba(16,185,129,0.08); }}
    .brand {{ display: inline-block; background: #059669; color: #ffffff; font-weight: 900; padding: 8px 14px; border-radius: 10px; font-size: 15px; letter-spacing: -0.3px; margin-bottom: 20px; }}
    .title {{ color: #064e3b; font-size: 20px; font-weight: 800; margin: 0 0 8px 0; }}
    .subtitle {{ color: #047857; font-size: 14px; margin: 0 0 20px 0; line-height: 1.5; }}
    .badge {{ display: inline-block; background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; font-size: 12px; font-weight: 700; padding: 6px 12px; border-radius: 8px; margin-bottom: 20px; }}
    .details {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; font-size: 13px; color: #334155; margin-bottom: 20px; }}
    .details-item {{ display: flex; justify-content: space-between; margin-bottom: 8px; }}
    .details-item:last-child {{ margin-bottom: 0; }}
    .label {{ color: #64748b; font-weight: 600; }}
    .val {{ font-weight: 700; color: #0f172a; font-family: monospace; }}
    .footer {{ font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #f1f5f9; padding-top: 16px; margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="brand">⚡ Ascendra AI</div>
    <h2 class="title">SMTP Configuration Verified</h2>
    <p class="subtitle">Your custom email sending credentials are active and ready to deliver outreach emails.</p>

    <div class="badge">
      ✅ Status: Connection Verified & Active
    </div>

    <div class="details">
      <div class="details-item">
        <span class="label">Sending Address:</span>
        <span class="val">{config.smtp_username}</span>
      </div>
      <div class="details-item">
        <span class="label">SMTP Host:</span>
        <span class="val">{config.smtp_host}:{config.smtp_port}</span>
      </div>
      <div class="details-item">
        <span class="label">Display Name:</span>
        <span class="val">{display}</span>
      </div>
    </div>

    <p style="font-size: 13px; color: #475569; line-height: 1.5; margin: 0;">
      You can now send personalized cold outreach and follow-up emails directly from your own email account with maximum deliverability.
    </p>

    <div class="footer">
      Ascendra AI Headhunting Engine &copy; 2026. All rights reserved.
    </div>
  </div>
</body>
</html>
"""
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        real_password = decrypt_credential(config.smtp_password)

        try:
            await aiosmtplib.send(
                msg,
                hostname=config.smtp_host,
                port=config.smtp_port,
                username=config.smtp_username,
                password=real_password,
                start_tls=True,
            )
            return True, f"Test email sent successfully to {recipient}"
        except Exception as e:
            logger.warning(f"SMTP test failed for {config.smtp_username}: {e}")
            return False, f"SMTP connection failed: {e}"

    @staticmethod
    async def _send_test_email_gmail_oauth(
        config: UserEmailConfig, recipient: str, db: AsyncSession | None = None
    ) -> tuple[bool, str]:
        """Send a test email via Gmail OAuth API.

        If the access token is expired, the provider will automatically
        refresh it. When a DB session is provided, the refreshed token
        is persisted so future requests don't fail.
        """
        from app.providers.email.gmail_oauth import GmailOAuthProvider
        from app.providers.email.base import EmailMessage

        display = config.display_name or config.smtp_username.split("@")[0]

        provider = GmailOAuthProvider(
            access_token=config.oauth_access_token or "",
            refresh_token=config.oauth_refresh_token,
            client_id=config.oauth_client_id,
            client_secret=config.oauth_client_secret,
        )

        message = EmailMessage(
            to_email=recipient,
            subject="Ascendra — Gmail OAuth Configuration Verified ✅",
            body_text=(
                "Ascendra — Gmail OAuth Verified\n\n"
                "Your Google account is connected and ready for outreach.\n"
                f"Sending as: {config.smtp_username}\n"
            ),
            body_html=(
                f'<div style="font-family: sans-serif; max-width: 520px; margin: 0 auto; '
                f'background: #fff; padding: 32px; border-radius: 16px; border: 1px solid #d1fae5;">'
                f'<div style="display: inline-block; background: #059669; color: #fff; font-weight: 900; '
                f'padding: 8px 14px; border-radius: 10px; font-size: 15px; margin-bottom: 20px;">⚡ Ascendra AI</div>'
                f'<h2 style="color: #064e3b; font-size: 20px; font-weight: 800;">Gmail OAuth Verified</h2>'
                f'<p style="color: #047857; font-size: 14px;">Your Google account is connected via OAuth. '
                f'No app password needed!</p>'
                f'<div style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; '
                f'font-size: 12px; font-weight: 700; padding: 6px 12px; border-radius: 8px; '
                f'display: inline-block; margin: 16px 0;">✅ Connected as: {config.smtp_username}</div>'
                f'<p style="font-size: 13px; color: #475569;">You can now send outreach emails directly '
                f'from your Gmail account.</p>'
                f'<div style="font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #f1f5f9; '
                f'padding-top: 16px; margin-top: 24px;">Ascendra AI &copy; 2026</div></div>'
            ),
            from_name=display,
        )

        try:
            result = await provider.send(message)
            if result.success:
                # Persist refreshed access token if it changed
                if db and provider.access_token and provider.access_token != config.oauth_access_token:
                    from app.core.security import encrypt_credential
                    config.oauth_access_token = encrypt_credential(provider.access_token)
                    await db.commit()
                    logger.info(f"Persisted refreshed Gmail OAuth token for {config.smtp_username}")
                return True, f"Test email sent via Gmail OAuth to {recipient}"
            else:
                return False, f"Gmail OAuth test failed: {result.error}"
        except Exception as e:
            logger.warning(f"Gmail OAuth test failed for {config.smtp_username}: {e}")
            return False, f"Gmail OAuth test failed: {e}"


email_config_service = EmailConfigService()

