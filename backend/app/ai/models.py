"""
Ascendra — AI Models.

Track every AI request and response for reproducibility.
"""

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class AIGeneration(Base):
    """Record of every AI generation for audit and reproducibility."""
    __tablename__ = "ai_generations"

    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    generation_type: Mapped[str] = mapped_column(String(50), nullable=False)  # resume, email, etc.
    prompt_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_used: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    input_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    # Reference to what was generated (resume_version_id, message_id, etc.)
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), nullable=True)

    def __repr__(self) -> str:
        return f"<AIGeneration {self.generation_type} [{self.model_used}]>"
