"""
Ascendra — Email Celery Tasks.

Queue-based email delivery per doc/09 §115:
  Approve → Queue → Worker → Provider → Delivery

Includes:
- Per-user SMTP credential resolution
- Click tracking link wrapping
- Open tracking pixel injection
- Real-time notification publishing after send
"""

import asyncio
import logging
import re
from urllib.parse import quote

from sqlalchemy import select

from app.auth.models import User, UserEmailConfig
from app.config import settings
from app.database import async_session_factory
from app.email.models import Conversation, Message, MessageStatus
from app.email.service import email_service
from app.notifications.models import NotificationType
from app.providers.email.base import EmailMessage
from app.providers.email.smtp import SMTPCredentials, smtp_provider
from app.workers.celery_app import celery_app

logger = logging.getLogger("ascendra.workers.email")


# ── Private Helpers ───────────────────────────────────────────


def _wrap_click_tracking_links(html: str, message_id: str, base_url: str) -> str:
    """Wrap all external href links with click-tracking redirect URLs."""
    def _replace_link(match: re.Match) -> str:
        url = match.group(1)
        if "email/track" in url:
            return match.group(0)  # Skip already-wrapped links
        wrapped = f"{base_url}/api/v1/email/track/click/{message_id}?target={quote(url, safe='')}"
        return f'href="{wrapped}"'

    return re.sub(r'href=["\']((https?://[^"\']+))["\']', _replace_link, html)


def _inject_tracking_pixel(html: str, message_id: str, base_url: str) -> str:
    """Append a 1x1 transparent tracking pixel to the HTML body."""
    pixel_url = f"{base_url}/api/v1/email/track/open/{message_id}"
    pixel_tag = (
        f'<img src="{pixel_url}" width="1" height="1" '
        f'style="display:none;width:1px;height:1px;" alt="" />'
    )
    return html + pixel_tag


async def _resolve_user_email_config(
    db, user_id: str
) -> UserEmailConfig | None:
    """
    Look up the user's per-user email config from the database.
    Returns the full UserEmailConfig ORM object so the dispatcher
    can read provider_type and OAuth fields.
    Returns None if no config exists.
    """
    result = await db.execute(
        select(UserEmailConfig).where(
            UserEmailConfig.user_id == user_id,
        ).order_by(UserEmailConfig.created_at.desc())
    )
    return result.scalars().first()


def _convert_markdown_to_pdf_bytes(markdown_text: str, title: str = "Tailored Resume") -> bytes | None:
    """Convert Markdown content to styled PDF bytes using PyMuPDF."""
    try:
        import fitz
        import re

        def parse_inline(text: str) -> str:
            t = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
            t = re.sub(r'\*(.*?)\*', r'<em>\1</em>', t)
            t = re.sub(r'`([^`]+)`', r'<code style="background:#f1f5f9;padding:1px 3px;">\1</code>', t)
            return t

        lines = markdown_text.split("\n")
        html_lines = []
        in_list = False

        for line in lines:
            trimmed = line.strip()
            if not trimmed:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                continue

            if trimmed.startswith("# "):
                if in_list: html_lines.append("</ul>"); in_list = False
                html_lines.append(f"<h1 style='font-size: 18pt; color: #0f172a; margin-top: 0; margin-bottom: 6pt; border-bottom: 2pt solid #059669; padding-bottom: 4pt;'>{parse_inline(trimmed[2:])}</h1>")
            elif trimmed.startswith("## "):
                if in_list: html_lines.append("</ul>"); in_list = False
                html_lines.append(f"<h2 style='font-size: 12pt; color: #047857; margin-top: 14pt; margin-bottom: 4pt; text-transform: uppercase; letter-spacing: 0.5pt; border-bottom: 1pt solid #cbd5e1; padding-bottom: 2pt;'>{parse_inline(trimmed[3:])}</h2>")
            elif trimmed.startswith("### "):
                if in_list: html_lines.append("</ul>"); in_list = False
                html_lines.append(f"<h3 style='font-size: 10.5pt; color: #1e293b; margin-top: 10pt; margin-bottom: 3pt;'>{parse_inline(trimmed[4:])}</h3>")
            elif trimmed.startswith("- ") or trimmed.startswith("* "):
                if not in_list: html_lines.append("<ul style='margin: 4pt 0 6pt 16pt; padding: 0;'>"); in_list = True
                html_lines.append(f"<li style='font-size: 9.5pt; color: #334155; margin-bottom: 3pt; line-height: 1.4;'>{parse_inline(trimmed[2:])}</li>")
            else:
                if in_list: html_lines.append("</ul>"); in_list = False
                html_lines.append(f"<p style='font-size: 9.5pt; color: #334155; margin: 3pt 0 6pt 0; line-height: 1.45;'>{parse_inline(trimmed)}</p>")

        if in_list:
            html_lines.append("</ul>")

        html_body = "".join(html_lines)
        full_html = f"<html><head><style>body {{ font-family: sans-serif; padding: 25pt; color: #1e293b; }}</style></head><body>{html_body}</body></html>"

        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        rect = fitz.Rect(36, 36, 559, 806)

        if hasattr(page, "insert_htmlbox"):
            page.insert_htmlbox(rect, full_html)
        else:
            story = fitz.Story(html=full_html)
            story.place(rect)
            device = fitz.Device(page)
            story.draw(device)

        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes
    except Exception as exc:
        logger.warning(f"Failed to render Markdown to PDF bytes: {exc}")
        return None


async def _publish_notification(db, user_id: str, success: bool, recipient: str) -> None:
    """Create a real-time notification after email send attempt."""
    try:
        from app.notifications.service import notification_service
        if success:
            await notification_service.create(
                db=db,
                user_id=user_id,
                type=NotificationType.EMAIL_SENT,
                title="Email Sent",
                message=f"Your email to {recipient} was delivered successfully.",
                entity_type="message",
            )
        else:
            await notification_service.create(
                db=db,
                user_id=user_id,
                type=NotificationType.EMAIL_FAILED,
                title="Email Failed",
                message=f"Failed to deliver email to {recipient}. Check your email settings.",
                entity_type="message",
            )
    except Exception as e:
        logger.warning(f"Failed to create send notification: {e}")


# ── Main Async Implementation ────────────────────────────────


async def _send_email_async(message_id: str) -> None:
    """Async implementation of the email sending task."""
    async with async_session_factory() as db:
        # 1. Fetch message and validate state
        result = await db.execute(
            select(Message).where(Message.id == message_id)
        )
        message = result.scalar_one_or_none()

        if not message:
            logger.error(f"Message {message_id} not found")
            return

        if message.status != MessageStatus.QUEUED:
            logger.warning(f"Message {message_id} is not queued (status: {message.status})")
            return

        # 2. Mark as sending (transition)
        message.status = MessageStatus.SENDING
        await db.commit()

        # 3. Resolve the sending user's identity
        convo_res = await db.execute(
            select(Conversation).where(Conversation.id == message.conversation_id)
        )
        convo = convo_res.scalar_one_or_none()

        user_id = convo.user_id if convo else None
        user_email = None
        user_name = None

        if user_id:
            usr_res = await db.execute(select(User).where(User.id == user_id))
            usr = usr_res.scalar_one_or_none()
            if usr:
                user_email = usr.email
                user_name = usr.full_name or usr.email.split("@")[0]

        # 4. Resolve per-user SMTP credentials (fall back to global .env)
        user_credentials = None
        if user_id:
            user_credentials = await _resolve_user_email_config(db, user_id)

        if user_credentials:
            logger.info(f"Using per-user email configuration for user {user_id[:8]} ({user_credentials.smtp_username})")
        else:
            # STRICT: Do NOT fall back to global .env SMTP credentials.
            # User must configure their own email credentials.
            error_reason = "NO_EMAIL_CREDENTIALS_CONFIGURED"
            logger.warning(
                f"No per-user SMTP credentials found for user {user_id[:8]} — "
                f"rejecting email send (no application fallback)."
            )
            message.status = MessageStatus.FAILED
            message.send_error = (
                "Email not sent: You have not configured your email credentials. "
                "Please go to Profile → Email Settings and add your SMTP / App Password "
                "to enable outreach email delivery."
            )
            await db.commit()

            # Publish notification prompting user to add credentials
            if user_id:
                try:
                    from app.notifications.service import notification_service
                    await notification_service.create(
                        db=db,
                        user_id=user_id,
                        type=NotificationType.EMAIL_FAILED,
                        title="Email Credentials Required",
                        message=(
                            f"Could not send email to {message.to_email}. "
                            "You need to configure your email credentials in Profile → Email Settings "
                            "before sending outreach emails."
                        ),
                        entity_type="message",
                    )
                except Exception as notif_err:
                    logger.warning(f"Failed to create credentials notification: {notif_err}")

            return  # Exit early — do not attempt to send

        # 5. Inject tracking into HTML body
        base_backend = settings.BACKEND_URL.rstrip("/")
        html_body = message.body_html or ""
        html_body = _wrap_click_tracking_links(html_body, str(message.id), base_backend)
        html_body = _inject_tracking_pixel(html_body, str(message.id), base_backend)

        # 6. Fetch candidate resume attachment if available
        attachments = []
        if user_id:
            try:
                # Priority 0: User explicitly chose a resume version in the outreach modal
                if message.resume_version_id:
                    from app.resumes.models import ResumeVersion, Resume
                    rv_res = await db.execute(select(ResumeVersion).where(ResumeVersion.id == message.resume_version_id))
                    rv = rv_res.scalar_one_or_none()
                    if rv and rv.markdown_content:
                        filename_clean = (rv.label or "Tailored_Resume").replace(" ", "_")
                        pdf_bytes = _convert_markdown_to_pdf_bytes(rv.markdown_content, title=rv.label or "Tailored Resume")
                        if pdf_bytes:
                            attachments.append({
                                "filename": f"{filename_clean}.pdf",
                                "content": pdf_bytes,
                                "content_type": "application/pdf"
                            })
                        else:
                            attachments.append({
                                "filename": f"{filename_clean}.md",
                                "content": rv.markdown_content.encode("utf-8"),
                                "content_type": "text/markdown"
                            })
                    elif not rv:
                        # resume_version_id might refer to a master resume
                        master_res = await db.execute(select(Resume).where(Resume.id == message.resume_version_id))
                        master = master_res.scalar_one_or_none()
                        if master and master.file_path:
                            from app.providers.storage.supabase import storage_provider
                            pdf_bytes = await storage_provider.download(master.file_path)
                            if pdf_bytes:
                                attachments.append({
                                    "filename": master.original_filename or "Resume.pdf",
                                    "content": pdf_bytes,
                                    "content_type": "application/pdf"
                                })

                # Priority 1: Linked tailored resume version for this application or job
                if not attachments and convo and convo.application_id:
                    from app.applications.models import Application
                    app_res = await db.execute(select(Application).where(Application.id == convo.application_id))
                    app = app_res.scalar_one_or_none()
                    if app:
                        from app.resumes.models import ResumeVersion
                        rv = None
                        if app.resume_version_id:
                            rv_res = await db.execute(select(ResumeVersion).where(ResumeVersion.id == app.resume_version_id))
                            rv = rv_res.scalar_one_or_none()
                        if not rv and app.job_id:
                            rv_res = await db.execute(
                                select(ResumeVersion)
                                .where(ResumeVersion.job_id == app.job_id, ResumeVersion.user_id == user_id)
                                .order_by(ResumeVersion.created_at.desc())
                            )
                            rv = rv_res.scalars().first()

                        if rv and rv.markdown_content:
                            filename_clean = (rv.label or "Tailored_Resume").replace(" ", "_")
                            pdf_bytes = _convert_markdown_to_pdf_bytes(rv.markdown_content, title=rv.label or "Tailored Resume")
                            if pdf_bytes:
                                attachments.append({
                                    "filename": f"{filename_clean}.pdf",
                                    "content": pdf_bytes,
                                    "content_type": "application/pdf"
                                })
                            else:
                                attachments.append({
                                    "filename": f"{filename_clean}.md",
                                    "content": rv.markdown_content.encode("utf-8"),
                                    "content_type": "text/markdown"
                                })

                # Priority 2: Master uploaded resume PDF
                if not attachments:
                    from app.resumes.models import Resume, ResumeStatus
                    res_query = await db.execute(
                        select(Resume).where(
                            Resume.user_id == user_id,
                            Resume.status.in_([ResumeStatus.READY, ResumeStatus.PARSED, ResumeStatus.UPLOADED])
                        ).order_by(Resume.created_at.desc())
                    )
                    master_resume = res_query.scalars().first()
                    if master_resume and master_resume.file_path:
                        try:
                            from app.providers.storage.supabase import storage_provider
                            pdf_bytes = await storage_provider.download(master_resume.file_path)
                            if pdf_bytes:
                                attachments.append({
                                    "filename": master_resume.original_filename or "Resume.pdf",
                                    "content": pdf_bytes,
                                    "content_type": "application/pdf"
                                })
                        except Exception as storage_err:
                            logger.warning(f"Could not download master resume attachment: {storage_err}")
            except Exception as att_err:
                logger.warning(f"Failed to attach resume to email: {att_err}")

        # 7. Build message object
        email_msg = EmailMessage(
            to_email=message.to_email,
            subject=message.subject,
            body_text=message.body_text or "",
            body_html=html_body,
            from_email=user_email,
            from_name=user_name,
            reply_to=user_email,
            attachments=attachments if attachments else None,
        )

        # Dispatch via configured provider type
        from app.core.security import decrypt_credential
        provider_type = str(user_credentials.provider_type or "SMTP").upper()

        if "GMAIL" in provider_type and (user_credentials.oauth_access_token or user_credentials.oauth_refresh_token):
            from app.providers.email.gmail_oauth import GmailOAuthProvider
            gmail_provider = GmailOAuthProvider(
                access_token=user_credentials.oauth_access_token or "",
                refresh_token=user_credentials.oauth_refresh_token,
                client_id=user_credentials.oauth_client_id,
                client_secret=user_credentials.oauth_client_secret,
            )
            send_result = await gmail_provider.send(email_msg)
            # Persist refreshed token if it changed during send
            if gmail_provider.access_token and gmail_provider.access_token != decrypt_credential(user_credentials.oauth_access_token or ""):
                from app.core.security import encrypt_credential
                user_credentials.oauth_access_token = encrypt_credential(gmail_provider.access_token)
                await db.commit()
                logger.info("Persisted refreshed Gmail OAuth token after send")

            # SMTP fallback: If Gmail OAuth failed, try SMTP before giving up
            if not send_result.success and user_credentials.smtp_username and user_credentials.smtp_password:
                logger.warning(
                    f"Gmail OAuth failed ({send_result.error}), falling back to SMTP"
                )
                try:
                    smtp_creds = SMTPCredentials(
                        host=user_credentials.smtp_host or "smtp.gmail.com",
                        port=user_credentials.smtp_port or 587,
                        username=user_credentials.smtp_username,
                        password=decrypt_credential(user_credentials.smtp_password),
                    )
                    send_result = await smtp_provider.send(email_msg, credentials=smtp_creds)
                    if send_result.success:
                        logger.info("SMTP fallback succeeded after Gmail OAuth failure")
                except Exception as smtp_err:
                    logger.warning(f"SMTP fallback also failed: {smtp_err}")

        elif "OUTLOOK" in provider_type and (user_credentials.oauth_access_token or user_credentials.oauth_refresh_token):
            from app.providers.email.outlook_oauth import OutlookOAuthProvider
            outlook_provider = OutlookOAuthProvider(
                access_token=user_credentials.oauth_access_token or "",
                refresh_token=user_credentials.oauth_refresh_token,
                client_id=user_credentials.oauth_client_id,
                client_secret=user_credentials.oauth_client_secret,
            )
            send_result = await outlook_provider.send(email_msg)
        else:
            # Build SMTPCredentials from the full UserEmailConfig for SMTP path
            smtp_creds = SMTPCredentials(
                host=user_credentials.smtp_host,
                port=user_credentials.smtp_port,
                username=user_credentials.smtp_username,
                password=decrypt_credential(user_credentials.smtp_password),
            )
            send_result = await smtp_provider.send(email_msg, credentials=smtp_creds)

        # 7. Update message status in DB
        if send_result.success:
            logger.info(f"Email successfully delivered to {message.to_email}")
            await email_service.mark_sent(
                db=db,
                message_id=message_id,
                provider_message_id=send_result.message_id,
            )
        else:
            logger.error(f"Email delivery FAILED to {message.to_email}: {send_result.error}")
            await email_service.mark_failed(
                db=db,
                message_id=message_id,
                error=send_result.error or "Unknown error",
            )

        # 8. Publish real-time notification
        if user_id:
            await _publish_notification(db, user_id, send_result.success, message.to_email)


# ── Celery Task Entry Point ──────────────────────────────────


@celery_app.task(bind=True, max_retries=3)
def send_email_task(self, message_id: str):
    """
    Celery task to send an email.
    Uses a fresh event loop per invocation to avoid 'Event loop is closed' errors.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_send_email_async(message_id))
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Failed to send email {message_id}: {exc}")
        raise self.retry(exc=exc, countdown=15)

