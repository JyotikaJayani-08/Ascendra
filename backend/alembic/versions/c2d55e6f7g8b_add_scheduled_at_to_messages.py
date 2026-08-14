"""add scheduled_at to messages and SCHEDULED status

Revision ID: c2d55e6f7g8b
Revises: b1c44d5e6f7a
Create Date: 2026-08-13 12:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c2d55e6f7g8b'
down_revision: Union[str, None] = 'b1c44d5e6f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add scheduled_at column for scheduled email sending
    op.add_column(
        'messages',
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
    )
    # Add SCHEDULED to the message_status enum
    op.execute("ALTER TYPE message_status ADD VALUE IF NOT EXISTS 'SCHEDULED' AFTER 'APPROVED'")


def downgrade() -> None:
    op.drop_column('messages', 'scheduled_at')
    # Note: PostgreSQL does not support removing enum values.
    # The SCHEDULED value will remain in the enum but will be unused.
