"""
Ascendra — Notes Service.

CRUD operations for user notes with proper ownership enforcement.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFound
from app.notes.models import Note
from app.notes.schemas import NoteCreate, NoteUpdate

logger = logging.getLogger("ascendra.notes")


class NoteService:
    """Encapsulates all note CRUD operations with ownership enforcement."""

    async def create(
        self, db: AsyncSession, user_id: str, note_in: NoteCreate
    ) -> Note:
        """Create a new note for the user."""
        note = Note(
            user_id=user_id,
            title=note_in.title,
            content=note_in.content,
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)
        logger.info(f"Note created: {note.id[:8]} by user {user_id[:8]}")
        return note

    async def list_for_user(self, db: AsyncSession, user_id: str) -> list[Note]:
        """List all notes for a user, newest first."""
        result = await db.execute(
            select(Note)
            .where(Note.user_id == user_id)
            .order_by(Note.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, db: AsyncSession, user_id: str, note_id: str) -> Note:
        """Get a single note, verifying ownership."""
        result = await db.execute(
            select(Note).where(Note.id == note_id, Note.user_id == user_id)
        )
        note = result.scalar_one_or_none()
        if not note:
            raise NotFound("Note")
        return note

    async def update(
        self,
        db: AsyncSession,
        user_id: str,
        note_id: str,
        note_in: NoteUpdate,
    ) -> Note:
        """Update a note's title and/or content."""
        note = await self.get(db, user_id, note_id)

        if note_in.title is not None:
            note.title = note_in.title
        if note_in.content is not None:
            note.content = note_in.content

        await db.commit()
        await db.refresh(note)
        return note

    async def delete(self, db: AsyncSession, user_id: str, note_id: str) -> None:
        """Delete a note permanently."""
        note = await self.get(db, user_id, note_id)
        await db.delete(note)
        await db.commit()
        logger.info(f"Note deleted: {note_id[:8]} by user {user_id[:8]}")


note_service = NoteService()
