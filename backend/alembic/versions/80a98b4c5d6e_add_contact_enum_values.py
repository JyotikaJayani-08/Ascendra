"""add contact enum values

Revision ID: 80a98b4c5d6e
Revises: 737e14a3563b
Create Date: 2026-07-26 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80a98b4c5d6e'
down_revision: Union[str, None] = '737e14a3563b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Note: COMMIT is required before ALTER TYPE ADD VALUE in some Postgres versions if running in a transaction block
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE contact_source ADD VALUE IF NOT EXISTS 'SCRAPED'")
        op.execute("ALTER TYPE contact_source ADD VALUE IF NOT EXISTS 'DISCOVERED'")
        op.execute("ALTER TYPE verification_status ADD VALUE IF NOT EXISTS 'UNVERIFIED'")


def downgrade() -> None:
    # Postgres doesn't easily support dropping enum values.
    # Leaving downgrade as pass.
    pass
