"""
Ascendra — Notes API Router.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.dependencies import get_current_user
from app.notes.schemas import NoteCreate, NoteUpdate, NoteResponse
from app.notes.service import note_service

router = APIRouter(prefix="/notes", tags=["Notes"])


@router.post("", response_model=NoteResponse)
async def create_note(
    note_in: NoteCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Create a new note."""
    return await note_service.create(db, user.id, note_in)


@router.get("", response_model=list[NoteResponse])
async def list_notes(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """List all notes for the current user."""
    return await note_service.list_for_user(db, user.id)


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Get a specific note."""
    return await note_service.get(db, user.id, note_id)


@router.patch("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    note_in: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Update a note."""
    return await note_service.update(db, user.id, note_id, note_in)


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: str,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user),
):
    """Delete a note."""
    await note_service.delete(db, user.id, note_id)
