"""
Ascendra — Contacts Router.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.schemas import MessageResponse
from app.contacts.schemas import ContactResponse, ContactListResponse, CreateContactRequest, UpdateContactRequest
from app.core.dependencies import get_current_active_user
from app.database import get_db
from app.contacts.service import contact_service

router = APIRouter(tags=["Contacts"])


@router.post("/contacts", response_model=ContactResponse, status_code=201)
async def create_contact(
    body: CreateContactRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually add a contact."""
    contact = await contact_service.create_manual(
        db=db, user_id=user.id, **body.model_dump()
    )
    return ContactResponse.model_validate(contact)


@router.post("/contacts/discover", response_model=list[ContactResponse])
async def discover_contacts(
    company_id: str,
    company_domain: str | None = None,
    job_description: str | None = None,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Discover recruiter/HR contacts using 3-layer discovery (Regex text extraction, domain patterns, Hunter/Apollo API)."""
    contacts = await contact_service.discover_contacts_for_job(
        db=db,
        user_id=user.id,
        company_id=company_id,
        company_domain=company_domain,
        job_description=job_description,
    )
    return [ContactResponse.model_validate(c) for c in contacts]


@router.get("/contacts", response_model=ContactListResponse)
async def list_user_contacts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all contacts added by the current user."""
    contacts, total = await contact_service.list_for_user(db=db, user_id=user.id, page=page, page_size=page_size)
    return ContactListResponse(
        items=[ContactResponse.model_validate(c) for c in contacts],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/contacts/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific contact."""
    contact = await contact_service.get(db=db, contact_id=contact_id)
    return ContactResponse.model_validate(contact)


@router.get("/companies/{company_id}/contacts", response_model=list[ContactResponse])
async def list_company_contacts(
    company_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all contacts for a company, ranked by confidence."""
    contacts = await contact_service.list_for_company(db=db, company_id=company_id)
    return [ContactResponse.model_validate(c) for c in contacts]


@router.patch("/contacts/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: str,
    body: UpdateContactRequest,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a contact."""
    contact = await contact_service.update(
        db=db, contact_id=contact_id, user_id=user.id,
        **body.model_dump(exclude_unset=True),
    )
    return ContactResponse.model_validate(contact)


@router.delete("/contacts/all", response_model=MessageResponse)
async def delete_all_contacts(
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all contacts for the current user."""
    count = await contact_service.delete_all_for_user(db=db, user_id=user.id)
    return MessageResponse(message=f"Deleted {count} contacts.")


@router.delete("/contacts/{contact_id}", response_model=MessageResponse)
async def delete_contact(
    contact_id: str,
    user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a manually-added contact."""
    await contact_service.delete(db=db, contact_id=contact_id, user_id=user.id)
    return MessageResponse(message="Contact deleted.")
