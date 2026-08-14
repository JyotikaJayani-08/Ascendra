"""add notes table

Revision ID: 161e55c02df8
Revises: 161e55c02df7
Create Date: 2026-07-21 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '161e55c02df8'
down_revision: Union[str, None] = '161e55c02df7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'notes',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['auth.users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notes_user_id'), 'notes', ['user_id'], unique=False)
    
    # Enable RLS
    op.execute('ALTER TABLE notes ENABLE ROW LEVEL SECURITY;')


def downgrade() -> None:
    op.drop_index(op.f('ix_notes_user_id'), table_name='notes')
    op.drop_table('notes')
