"""
Ascendra — Resume Service.

Upload, parse, version management.
"""

import logging

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateTransition, NotFound, PermissionDenied, ValidationError
from app.resumes.models import (
    Resume,
    ResumeStatus,
    ResumeVersion,
    ResumeVersionSource,
    ResumeVersionStatus,
)

logger = logging.getLogger("ascendra.resumes")

ALLOWED_MIME_TYPES = {"application/pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class ResumeService:

    # ── Upload ────────────────────────────────────────────────

    async def upload_resume(
        self,
        db: AsyncSession,
        user_id: str,
        filename: str,
        file_content: bytes,
        mime_type: str,
    ) -> Resume:
        """
        Validate and store a new resume upload.
        Actual file is stored via StorageProvider; metadata goes to DB.
        """
        # Validate
        if mime_type not in ALLOWED_MIME_TYPES:
            raise ValidationError("Only PDF files are supported.")
        if len(file_content) > MAX_FILE_SIZE:
            raise ValidationError("File size must be under 10 MB.")
        if len(file_content) == 0:
            raise ValidationError("File is empty.")

        # Store file via provider (imported at runtime to avoid circular deps)
        from app.providers.storage.supabase import storage_provider

        file_path = f"{user_id}/resumes/original/{filename}"
        await storage_provider.upload(file_path, file_content, mime_type)

        # Create DB record
        resume = Resume(
            user_id=user_id,
            original_filename=filename,
            file_path=file_path,
            file_size_bytes=len(file_content),
            mime_type=mime_type,
            status=ResumeStatus.UPLOADED,
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)

        logger.info(f"Resume uploaded: {filename} by user {user_id[:8]}")
        return resume

    # ── Parsing ───────────────────────────────────────────────

    async def mark_parsing(self, db: AsyncSession, resume_id: str) -> Resume:
        """Transition resume to PARSING state."""
        resume = await self._get_resume(db, resume_id)
        if resume.status != ResumeStatus.UPLOADED:
            raise InvalidStateTransition(resume.status, ResumeStatus.PARSING)
        resume.status = ResumeStatus.PARSING
        await db.commit()
        return resume

    async def complete_parsing(
        self,
        db: AsyncSession,
        resume_id: str,
        structured_data: dict,
        raw_text: str,
    ) -> Resume:
        """Store parsed data and transition to PARSED."""
        resume = await self._get_resume(db, resume_id)
        resume.structured_data = structured_data
        resume.raw_text = raw_text
        resume.status = ResumeStatus.PARSED
        await db.commit()
        await db.refresh(resume)

        # Auto-create version 1 (the original)
        await self._create_original_version(db, resume)

        logger.info(f"Resume parsed: {resume.id[:8]}")
        return resume

    # ── Versions ──────────────────────────────────────────────

    async def _create_original_version(
        self, db: AsyncSession, resume: Resume
    ) -> ResumeVersion:
        """Create version 1 from the parsed original resume."""
        version = ResumeVersion(
            resume_id=resume.id,
            user_id=resume.user_id,
            version_number=1,
            source=ResumeVersionSource.ORIGINAL,
            status=ResumeVersionStatus.APPROVED,
            structured_data=resume.structured_data,
            label="Original Resume",
        )
        db.add(version)
        resume.status = ResumeStatus.READY
        await db.commit()
        return version

    async def create_ai_version(
        self,
        db: AsyncSession,
        resume_id: str,
        user_id: str,
        structured_data: dict,
        markdown_content: str,
        job_id: str | None,
        prompt_version: str,
        model_used: str,
        label: str = "AI Optimized",
    ) -> ResumeVersion:
        """Create a new AI-generated resume version."""
        resume = await self._get_resume(db, resume_id)
        if resume.user_id != user_id:
            raise PermissionDenied()

        # Get next version number
        result = await db.execute(
            select(func.max(ResumeVersion.version_number)).where(
                ResumeVersion.resume_id == resume_id
            )
        )
        max_version = result.scalar() or 0

        version = ResumeVersion(
            resume_id=resume_id,
            user_id=user_id,
            version_number=max_version + 1,
            source=ResumeVersionSource.AI_GENERATED,
            status=ResumeVersionStatus.GENERATED,
            structured_data=structured_data,
            markdown_content=markdown_content,
            job_id=job_id,
            prompt_version=prompt_version,
            model_used=model_used,
            label=label,
        )
        db.add(version)
        await db.commit()
        await db.refresh(version)

        logger.info(f"Resume version v{version.version_number} created for {resume_id[:8]}")
        return version

    async def approve_version(
        self, db: AsyncSession, version_id: str, user_id: str
    ) -> ResumeVersion:
        """Approve a generated resume version."""
        result = await db.execute(
            select(ResumeVersion).where(ResumeVersion.id == version_id)
        )
        version = result.scalar_one_or_none()
        if not version:
            raise NotFound("Resume Version")
        if version.user_id != user_id:
            raise PermissionDenied()
        if version.status != ResumeVersionStatus.GENERATED:
            raise InvalidStateTransition(version.status, ResumeVersionStatus.APPROVED)

        version.status = ResumeVersionStatus.APPROVED
        await db.commit()
        return version

    # ── Queries ───────────────────────────────────────────────

    async def get_user_resumes(
        self, db: AsyncSession, user_id: str
    ) -> list[Resume]:
        """List all resumes for a user."""
        result = await db.execute(
            select(Resume)
            .where(
                Resume.user_id == user_id,
                Resume.status != ResumeStatus.ARCHIVED,
            )
            .order_by(Resume.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_resume(
        self, db: AsyncSession, resume_id: str, user_id: str
    ) -> Resume:
        """Get a single resume, verifying ownership."""
        resume = await self._get_resume(db, resume_id)
        if resume.user_id != user_id:
            raise PermissionDenied()
        return resume

    async def get_resume_versions(
        self, db: AsyncSession, resume_id: str, user_id: str
    ) -> list[ResumeVersion]:
        """List all versions of a specific resume."""
        resume = await self._get_resume(db, resume_id)
        if resume.user_id != user_id:
            raise PermissionDenied()
        result = await db.execute(
            select(ResumeVersion)
            .where(ResumeVersion.resume_id == resume_id)
            .order_by(ResumeVersion.version_number.desc())
        )
        return list(result.scalars().all())

    async def get_all_user_versions(
        self, db: AsyncSession, user_id: str
    ) -> list[ResumeVersion]:
        """List all tailored/AI resume versions for a user across all resumes."""
        result = await db.execute(
            select(ResumeVersion)
            .options(joinedload(ResumeVersion.resume))
            .where(ResumeVersion.user_id == user_id)
            .order_by(ResumeVersion.created_at.desc())
        )
        return list(result.unique().scalars().all())

    async def compare_version_with_original(
        self, db: AsyncSession, version_id: str, user_id: str
    ) -> dict:
        """
        Backend comparison service:
        Compares an AI-tailored resume version against its original base resume.
        Calculates side-by-side diff metrics: original skills, matched keywords,
        missing skills, added keywords, base ATS score vs tailored ATS score,
        and all sibling versions for dropdown selection.
        """
        res = await db.execute(
            select(ResumeVersion)
            .options(joinedload(ResumeVersion.resume))
            .where(
                ResumeVersion.id == version_id,
                ResumeVersion.user_id == user_id,
            )
        )
        version = res.scalar_one_or_none()
        if not version:
            raise NotFound("ResumeVersion")

        original_resume = version.resume
        orig_sdata = (original_resume.structured_data or {}) if original_resume else {}
        tailored_sdata = version.structured_data or {}

        # Safely flatten original skills from string, list, or category dict
        orig_skills_raw = orig_sdata.get("skills", [])
        flat_orig_skills: list[str] = []
        if isinstance(orig_skills_raw, list):
            for item in orig_skills_raw:
                if isinstance(item, str):
                    flat_orig_skills.append(item)
                elif isinstance(item, dict):
                    for v in item.values():
                        if isinstance(v, list):
                            flat_orig_skills.extend([str(x) for x in v if x])
                        elif isinstance(v, str):
                            flat_orig_skills.append(v)
        elif isinstance(orig_skills_raw, dict):
            for v in orig_skills_raw.values():
                if isinstance(v, list):
                    flat_orig_skills.extend([str(x) for x in v if x])
                elif isinstance(v, str):
                    flat_orig_skills.append(v)
        elif isinstance(orig_skills_raw, str):
            flat_orig_skills = [orig_skills_raw]

        matched = tailored_sdata.get("matched_keywords", [])
        if not isinstance(matched, list):
            matched = []
        missing = tailored_sdata.get("missing_skills", [])
        if not isinstance(missing, list):
            missing = []

        ats_score = tailored_sdata.get("ats_score", 0)
        ats_feedback = tailored_sdata.get("ats_feedback")

        # Newly added keywords (matched keywords that were NOT in the original resume)
        orig_skills_set = {s.lower().strip() for s in flat_orig_skills if isinstance(s, str)}
        added_keywords = [
            kw for kw in matched
            if isinstance(kw, str) and kw.lower().strip() not in orig_skills_set
        ]

        # Estimate original base resume ATS score before tailoring
        total_req_skills = len(matched) + len(missing)
        orig_matched_count = len(matched) - len(added_keywords)
        if total_req_skills > 0:
            original_ats_score = max(10, round((orig_matched_count / total_req_skills) * 100))
        else:
            original_ats_score = max(10, (ats_score or 50) - 25)

        score_improvement = (ats_score or 0) - original_ats_score

        # Get all sibling versions for dropdown selection
        sibling_versions = []
        if original_resume:
            sib_res = await db.execute(
                select(ResumeVersion.id, ResumeVersion.version_number, ResumeVersion.label, ResumeVersion.created_at)
                .where(ResumeVersion.resume_id == original_resume.id)
                .order_by(ResumeVersion.version_number.desc())
            )
            for row in sib_res.all():
                sibling_versions.append({
                    "id": row.id,
                    "version_number": row.version_number,
                    "label": row.label,
                    "created_at": row.created_at.isoformat() if row.created_at else "",
                })

        orig_snippet = (
            original_resume.raw_text
            if original_resume and original_resume.raw_text
            else orig_sdata.get("summary", "")
        )

        return {
            "version_id": version.id,
            "resume_id": version.resume_id,
            "original_filename": original_resume.original_filename if original_resume else "Master Resume",
            "version_label": version.label,
            "version_number": version.version_number,
            "original_ats_score": original_ats_score,
            "ats_score": ats_score,
            "score_improvement": score_improvement,
            "ats_feedback": ats_feedback,
            "original_skills": flat_orig_skills,
            "matched_keywords": matched,
            "missing_skills": missing,
            "added_keywords": added_keywords,
            "original_text_snippet": orig_snippet,
            "tailored_markdown": version.markdown_content,
            "sibling_versions": sibling_versions,
            "created_at": version.created_at,
        }

    async def _unlink_versions_from_applications(self, db: AsyncSession, version_ids: list[str]) -> None:
        """Unlink applications from resume versions before deletion to prevent FK violation."""
        if not version_ids:
            return
        from app.applications.models import Application
        await db.execute(
            update(Application)
            .where(Application.resume_version_id.in_(version_ids))
            .values(resume_version_id=None)
        )

    async def delete_resume(
        self, db: AsyncSession, resume_id: str, user_id: str
    ) -> None:
        """Hard-delete a resume and its associated storage file."""
        resume = await self._get_resume(db, resume_id)
        if resume.user_id != user_id:
            raise PermissionDenied()

        # Find associated version IDs to unlink from applications
        ver_res = await db.execute(
            select(ResumeVersion.id).where(ResumeVersion.resume_id == resume_id)
        )
        version_ids = list(ver_res.scalars().all())
        if version_ids:
            await self._unlink_versions_from_applications(db, version_ids)

        # Attempt to delete file from Supabase storage
        if resume.file_path:
            try:
                from app.providers.storage.supabase import storage_provider
                await storage_provider.delete(resume.file_path)
            except Exception as e:
                logger.warning(f"Failed to delete resume file from storage: {e}")

        await db.delete(resume)
        await db.commit()
        logger.info(f"Resume hard-deleted: {resume_id[:8]}")

    async def bulk_delete_resumes(
        self, db: AsyncSession, resume_ids: list[str], user_id: str
    ) -> int:
        """Bulk delete multiple resumes by IDs in a single batch."""
        result = await db.execute(
            select(Resume).where(
                Resume.id.in_(resume_ids),
                Resume.user_id == user_id
            )
        )
        resumes = result.scalars().all()
        if not resumes:
            return 0

        target_ids = [r.id for r in resumes]
        ver_res = await db.execute(
            select(ResumeVersion.id).where(ResumeVersion.resume_id.in_(target_ids))
        )
        version_ids = list(ver_res.scalars().all())
        if version_ids:
            await self._unlink_versions_from_applications(db, version_ids)

        file_paths = [r.file_path for r in resumes if r.file_path]
        if file_paths:
            try:
                from app.providers.storage.supabase import storage_provider
                await storage_provider.delete_many(file_paths)
            except Exception as e:
                logger.warning(f"Failed batch storage deletion: {e}")

        await db.execute(delete(Resume).where(Resume.id.in_(target_ids)))
        await db.commit()
        logger.info(f"Bulk deleted {len(target_ids)} resumes for user {user_id[:8]}")
        return len(target_ids)

    async def delete_all_resumes(
        self, db: AsyncSession, user_id: str
    ) -> int:
        """Delete all uploaded base resumes belonging to user in a single batch."""
        result = await db.execute(
            select(Resume).where(Resume.user_id == user_id)
        )
        resumes = result.scalars().all()
        if not resumes:
            return 0

        target_ids = [r.id for r in resumes]
        ver_res = await db.execute(
            select(ResumeVersion.id).where(ResumeVersion.user_id == user_id)
        )
        version_ids = list(ver_res.scalars().all())
        if version_ids:
            await self._unlink_versions_from_applications(db, version_ids)

        file_paths = [r.file_path for r in resumes if r.file_path]
        if file_paths:
            try:
                from app.providers.storage.supabase import storage_provider
                await storage_provider.delete_many(file_paths)
            except Exception as e:
                logger.warning(f"Failed batch storage deletion: {e}")

        await db.execute(delete(Resume).where(Resume.id.in_(target_ids)))
        await db.commit()
        logger.info(f"Deleted all {len(target_ids)} resumes for user {user_id[:8]}")
        return len(target_ids)

    async def delete_version(
        self, db: AsyncSession, version_id: str, user_id: str
    ) -> None:
        """Delete a single tailored resume version."""
        result = await db.execute(
            select(ResumeVersion).where(
                ResumeVersion.id == version_id,
                ResumeVersion.user_id == user_id
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            raise NotFound("ResumeVersion")
        await self._unlink_versions_from_applications(db, [version_id])
        await db.delete(version)
        await db.commit()
        logger.info(f"Resume version deleted: {version_id[:8]}")

    async def bulk_delete_versions(
        self, db: AsyncSession, version_ids: list[str], user_id: str
    ) -> int:
        """Bulk delete multiple tailored resume versions in a single SQL query."""
        await self._unlink_versions_from_applications(db, version_ids)
        result = await db.execute(
            delete(ResumeVersion).where(
                ResumeVersion.id.in_(version_ids),
                ResumeVersion.user_id == user_id
            )
        )
        count = result.rowcount or len(version_ids)
        await db.commit()
        logger.info(f"Bulk deleted resume versions for user {user_id[:8]}")
        return count

    async def delete_all_versions(
        self, db: AsyncSession, user_id: str
    ) -> int:
        """Delete all tailored resume versions for user in a single SQL query."""
        ver_res = await db.execute(
            select(ResumeVersion.id).where(ResumeVersion.user_id == user_id)
        )
        version_ids = list(ver_res.scalars().all())
        if version_ids:
            await self._unlink_versions_from_applications(db, version_ids)

        result = await db.execute(
            delete(ResumeVersion).where(ResumeVersion.user_id == user_id)
        )
        count = result.rowcount or 0
        await db.commit()
        logger.info(f"Deleted all resume versions for user {user_id[:8]}")
        return count

    async def get_stats(self, db: AsyncSession, user_id: str) -> dict[str, int]:
        """Get resume stats for dashboard."""
        resume_count_result = await db.execute(
            select(func.count()).select_from(Resume).where(
                Resume.user_id == user_id,
                Resume.status != ResumeStatus.ARCHIVED,
            )
        )
        total_resumes = resume_count_result.scalar() or 0

        version_count_result = await db.execute(
            select(func.count()).select_from(ResumeVersion).where(
                ResumeVersion.user_id == user_id
            )
        )
        total_versions = version_count_result.scalar() or 0

        return {
            "total_resumes": total_resumes,
            "total_resume_versions": total_versions
        }

    # ── Internal ──────────────────────────────────────────────

    async def _get_resume(self, db: AsyncSession, resume_id: str) -> Resume:
        result = await db.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()
        if not resume:
            raise NotFound("Resume")
        return resume


resume_service = ResumeService()
