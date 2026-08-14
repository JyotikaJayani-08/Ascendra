"""
Ascendra — Resume Celery Tasks.

Background parsing pipeline per doc/06 §46-47:
  Upload → Validate → Parse (AI) → Structure → Store → Ready

Includes:
- Robust event loop management for Celery
- Real-time notification publishing after parse
- Gemini primary / Groq fallback AI parsing
"""

import asyncio
import json
import logging

from sqlalchemy import select

from app.ai.service import ai_service
from app.database import async_session_factory
from app.notifications.models import NotificationType
from app.providers.storage.supabase import storage_provider
from app.resumes.models import Resume, ResumeStatus
from app.resumes.service import resume_service
from app.workers.celery_app import celery_app

import app.auth.models  # noqa: F401 — ensure model registry
import app.workspaces.models  # noqa: F401 — ensure model registry

logger = logging.getLogger("ascendra.workers.resume")


# ── Private Helpers ───────────────────────────────────────────


async def _publish_parse_notification(
    db, user_id: str, resume_name: str, success: bool, error_msg: str | None = None
) -> None:
    """Create a real-time notification after resume parse attempt."""
    try:
        from app.notifications.service import notification_service
        if success:
            await notification_service.create(
                db=db,
                user_id=user_id,
                type=NotificationType.RESUME_PARSED,
                title="Resume Parsed",
                message=f"Your resume '{resume_name}' has been parsed and is ready to use.",
                entity_type="resume",
            )
        else:
            await notification_service.create(
                db=db,
                user_id=user_id,
                type=NotificationType.SYSTEM,
                title="Resume Parsing Failed",
                message=f"Failed to parse '{resume_name}': {error_msg or 'Unknown error'}",
                entity_type="resume",
            )
    except Exception as e:
        logger.warning(f"Failed to create parse notification: {e}")


def _extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract raw text from a PDF file using PyMuPDF."""
    import fitz
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        raw_text = ""
        for page in doc:
            raw_text += page.get_text()
        return raw_text
    finally:
        doc.close()


async def _parse_with_ai(raw_text: str) -> dict:
    """
    Use AI (Gemini primary, Groq fallback) to convert raw resume
    text into structured JSON.
    """
    from app.providers.ai.gemini import gemini_provider
    from app.providers.ai.groq import groq_provider

    parsing_prompt = (
        "Parse the following resume text into a structured JSON object. "
        "Include fields for 'personal_info', 'summary', 'experience', "
        "'education', 'skills', and 'projects':\n\n"
        f"{raw_text[:20000]}"
    )
    system_prompt = "You are an expert resume parser. Extract information accurately."

    try:
        ai_response = await gemini_provider.generate_structured(
            prompt=parsing_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
        )
    except Exception as gemini_err:
        logger.warning(f"Gemini resume parsing failed ({gemini_err}). Falling back to Groq...")
        ai_response = await groq_provider.generate_structured(
            prompt=parsing_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
        )

    try:
        return json.loads(ai_response.content)
    except json.JSONDecodeError:
        return {"raw_parsing_error": "Failed to decode JSON", "extracted_text": raw_text[:5000]}


# ── Main Async Implementation ────────────────────────────────


async def _process_uploaded_resume_async(resume_id: str) -> None:
    """Async implementation to parse a resume PDF and extract JSON data."""
    async with async_session_factory() as db:
        # 1. Fetch resume and validate state
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()
        if not resume:
            logger.error(f"Resume {resume_id} not found")
            return

        if resume.status != ResumeStatus.UPLOADED:
            logger.warning(f"Resume {resume_id} is not in UPLOADED state")
            return

        # 2. Mark as parsing (state transition)
        await resume_service.mark_parsing(db=db, resume_id=resume_id)

        try:
            # 3. Download file from storage
            pdf_bytes = await storage_provider.download(resume.file_path)

            # 4. Extract raw text in background thread to keep event loop free
            raw_text = await asyncio.to_thread(_extract_text_from_pdf, pdf_bytes)
            if not raw_text.strip():
                raise ValueError("Could not extract any text from the PDF.")

            # 5. AI parsing
            structured_data = await _parse_with_ai(raw_text)

            # 6. Complete parsing and auto-generate the first ResumeVersion
            await resume_service.complete_parsing(
                db=db,
                resume_id=resume_id,
                structured_data=structured_data,
                raw_text=raw_text,
            )
            logger.info(f"Successfully parsed resume {resume_id}")

            # 7. Notify user of success
            await _publish_parse_notification(
                db, resume.user_id, resume.original_filename, success=True
            )

        except Exception as e:
            logger.error(f"Failed to parse resume {resume_id}: {e}")
            # Notify user of failure
            await _publish_parse_notification(
                db, resume.user_id, resume.original_filename,
                success=False, error_msg=str(e)
            )


# ── Celery Task Entry Points ─────────────────────────────────


@celery_app.task(bind=True, max_retries=2)
def process_uploaded_resume_task(self, resume_id: str):
    """
    Background task to parse an uploaded PDF resume into structured JSON.
    Uses a fresh event loop per invocation to avoid 'Event loop is closed' errors.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_process_uploaded_resume_async(resume_id))
        finally:
            loop.close()
    except Exception as exc:
        logger.error(f"Resume parsing task failed for {resume_id}: {exc}")
        raise self.retry(exc=exc, countdown=30)


@celery_app.task
def render_resume_pdf_task(resume_version_id: str):
    """
    Background task to render a ResumeVersion's markdown to PDF.
    (Handled by frontend for MVP per user alignment)
    """
    logger.info(f"Skipping PDF render for {resume_version_id} (handled by frontend).")
