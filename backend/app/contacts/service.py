"""
Ascendra — Contact Service.
"""

import re
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.contacts.models import Contact, ContactSource, VerificationStatus
from app.core.exceptions import NotFound, PermissionDenied
from app.providers.contacts.hunter import hunter_provider

logger = logging.getLogger("ascendra.contacts")


class ContactService:

    async def create_manual(
        self,
        db: AsyncSession,
        user_id: str,
        company_id: str,
        full_name: str,
        job_title: str | None = None,
        email: str | None = None,
        linkedin_url: str | None = None,
        notes: str | None = None,
    ) -> Contact:
        """Create a manually-added contact."""
        contact = Contact(
            company_id=company_id,
            full_name=full_name,
            job_title=job_title,
            email=email,
            linkedin_url=linkedin_url,
            source=ContactSource.MANUAL,
            confidence_score=0.8,  # Manual = user trusts this
            verification_status=VerificationStatus.UNKNOWN,
            notes=notes,
            added_by_user_id=user_id,
        )
        db.add(contact)
        await db.commit()
        await db.refresh(contact)

        logger.info(f"Contact created: {full_name} for company {company_id[:8]}")
        return contact

    async def get(self, db: AsyncSession, contact_id: str) -> Contact:
        result = await db.execute(
            select(Contact).where(Contact.id == contact_id)
        )
        contact = result.scalar_one_or_none()
        if not contact:
            raise NotFound("Contact")
        return contact

    async def list_for_company(
        self, db: AsyncSession, company_id: str
    ) -> list[Contact]:
        """List all contacts for a company, ranked by confidence."""
        result = await db.execute(
            select(Contact)
            .where(Contact.company_id == company_id)
            .order_by(Contact.confidence_score.desc())
        )
        return list(result.scalars().all())

    async def list_for_user(
        self, db: AsyncSession, user_id: str, page: int = 1, page_size: int = 25
    ) -> tuple[list[Contact], int]:
        """List all contacts added by a specific user."""
        query = select(Contact).where(Contact.added_by_user_id == user_id)
        
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar() or 0
        
        query = query.order_by(Contact.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await db.execute(query)
        return list(result.scalars().all()), total

    async def update(
        self,
        db: AsyncSession,
        contact_id: str,
        user_id: str,
        **fields,
    ) -> Contact:
        """Update a contact (only user-added contacts can be modified)."""
        contact = await self.get(db, contact_id)
        if contact.added_by_user_id and contact.added_by_user_id != user_id:
            raise PermissionDenied()

        for key, value in fields.items():
            if value is not None and hasattr(contact, key):
                setattr(contact, key, value)

        await db.commit()
        await db.refresh(contact)
        return contact

    async def delete(
        self, db: AsyncSession, contact_id: str, user_id: str
    ) -> None:
        """Delete a manually-added contact."""
        contact = await self.get(db, contact_id)
        if contact.source != ContactSource.MANUAL:
            raise PermissionDenied()
        if contact.added_by_user_id and contact.added_by_user_id != user_id:
            raise PermissionDenied()
        await db.delete(contact)
        await db.commit()

    async def delete_all_for_user(
        self, db: AsyncSession, user_id: str
    ) -> int:
        """Delete all contacts added by this user. Returns count of deleted contacts."""
        from sqlalchemy import delete as sa_delete
        result = await db.execute(
            sa_delete(Contact).where(Contact.added_by_user_id == user_id)
        )
        await db.commit()
        count = result.rowcount
        logger.info(f"Bulk-deleted {count} contacts for user {user_id[:8]}")
        return count

    async def discover_contacts_for_job(
        self,
        db: AsyncSession,
        user_id: str,
        company_id: str,
        company_domain: str | None = None,
        job_description: str | None = None,
    ) -> list[Contact]:
        """
        Contact Discovery Engine:
        Layer 1: NLP/Regex email extraction from job description text.
        Layer 2: Hunter.io verified domain search for actual recruiting/HR professionals.
        """
        # Ensure company record exists in DB to prevent FK or Unique Domain violation
        from app.jobs.models import Company
        comp_res = await db.execute(
            select(Company).where(
                (Company.id == company_id) | 
                ((Company.domain == company_domain) & (Company.domain.is_not(None)))
            )
        )
        company = comp_res.scalars().first()
        if company:
            company_id = company.id  # Use existing company ID if domain already exists
        else:
            clean_name = company_domain.replace("https://", "").replace("http://", "").strip("/").split("/")[0].capitalize() if company_domain else "Target Company"
            company = Company(
                id=company_id,
                name=clean_name,
                domain=company_domain,
            )
            db.add(company)
            await db.flush()

        discovered: list[Contact] = []

        # Layer 1: Regex extraction from job description text
        if job_description:
            emails = set(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", job_description))
            for email in emails:
                # Filter out generic platform/system emails
                if not any(email.endswith(domain) for domain in ["example.com", "w3.org", "schema.org"]):
                    contact = Contact(
                        company_id=company_id,
                        full_name="Extracted Recruiter",
                        job_title="Hiring Contact",
                        email=email,
                        source=ContactSource.SCRAPED,
                        confidence_score=0.85,
                        verification_status=VerificationStatus.UNVERIFIED,
                        added_by_user_id=user_id,
                    )
                    discovered.append(contact)

        # Layer 2: Hunter.io domain search (actual verified personnel)
        if company_domain and settings.HUNTER_API_KEY:
            clean_domain = company_domain.replace("https://", "").replace("http://", "").strip("/").split("/")[0]
            hunter_contacts = await hunter_provider.find_contacts(
                company_name=company.name if company else "", company_domain=clean_domain
            )
            for hc in hunter_contacts:
                contact = Contact(
                    company_id=company_id,
                    full_name=hc.full_name,
                    job_title=hc.job_title or "Recruiter",
                    email=hc.email,
                    linkedin_url=hc.linkedin_url,
                    source=ContactSource.HUNTER,
                    confidence_score=hc.confidence,
                    verification_status=VerificationStatus.VERIFIED if hc.confidence > 0.8 else VerificationStatus.UNVERIFIED,
                    added_by_user_id=user_id,
                )
                discovered.append(contact)

        # Persist discovered contacts (skip duplicates)
        if discovered:
            # Fetch existing emails for this company to avoid duplicates
            existing_result = await db.execute(
                select(Contact.email).where(
                    Contact.company_id == company_id,
                    Contact.email.is_not(None),
                )
            )
            existing_emails = {row[0].lower() for row in existing_result.all() if row[0]}

            new_contacts = []
            for c in discovered:
                if c.email and c.email.lower() not in existing_emails:
                    db.add(c)
                    existing_emails.add(c.email.lower())  # Prevent intra-batch duplicates
                    new_contacts.append(c)

            if new_contacts:
                await db.commit()
            discovered = new_contacts

        logger.info(f"Discovered {len(discovered)} contacts for company {company_id[:8]}")
        return discovered


contact_service = ContactService()
