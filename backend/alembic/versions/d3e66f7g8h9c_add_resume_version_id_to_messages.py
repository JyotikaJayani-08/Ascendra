"""add resume_version_id to messages

Revision ID: d3e66f7g8h9c
Revises: c2d55e6f7g8b
Create Date: 2026-08-14 17:47:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'd3e66f7g8h9c'
down_revision: Union[str, None] = 'c2d55e6f7g8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add resume_version_id column to messages table
    op.add_column(
        'messages',
        sa.Column('resume_version_id', UUID(as_uuid=False), nullable=True),
    )
    # Create partial index for performance
    op.create_index(
        'idx_messages_resume_version_id',
        'messages',
        ['resume_version_id'],
        unique=False,
        postgresql_where=sa.text('resume_version_id IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('idx_messages_resume_version_id', table_name='messages')
    op.drop_column('messages', 'resume_version_id')
