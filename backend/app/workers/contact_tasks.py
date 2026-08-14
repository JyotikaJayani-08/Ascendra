"""
Ascendra — Contact Celery Tasks.
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.contacts.service import contact_service
from app.database import async_session_factory
from app.jobs.models import Company
from app.providers.contacts.hunter import hunter_provider
from app.workers.celery_app import celery_app

logger = logging.getLogger("ascendra.workers.contacts")


async def _auto_discover_contacts_async(company_id: str):
    """Async implementation to discover contacts for a company."""
    async with async_session_factory() as db:
        try:
            result = await db.execute(select(Company).where(Company.id == company_id))
            company = result.scalar_one_or_none()
            if not company:
                logger.error(f"Company {company_id} not found")
                return

            if not company.domain:
                logger.info(f"Company {company.name} has no domain. Cannot run Hunter discovery.")
                return

            contacts = await hunter_provider.find_contacts(
                company_name=company.name,
                company_domain=company.domain
            )
            
            count = 0
            for contact in contacts:
                # We use create_manual but attribute it to SYSTEM (None user_id)
                from app.contacts.models import Contact, ContactSource, VerificationStatus
                
                new_contact = Contact(
                    company_id=company_id,
                    full_name=contact.full_name,
                    job_title=contact.job_title,
                    email=contact.email,
                    linkedin_url=contact.linkedin_url,
                    source=ContactSource.HUNTER,
                    confidence_score=contact.confidence,
                    verification_status=VerificationStatus.ESTIMATED,
                    added_by_user_id=None,  # System generated
                )
                db.add(new_contact)
                count += 1
                
            if count > 0:
                await db.commit()
                logger.info(f"Discovered {count} contacts for company {company.name}")
                
        except Exception as e:
            logger.error(f"Contact discovery failed for company {company_id}: {e}")


@celery_app.task
def auto_discover_contacts_task(company_id: str):
    """
    Background task to automatically search for contacts via Hunter when a new company is added.
    """
    from asgiref.sync import async_to_sync
    async_to_sync(_auto_discover_contacts_async)(company_id)
