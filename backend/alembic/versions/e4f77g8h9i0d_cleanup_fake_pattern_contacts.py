"""cleanup fake pattern contacts

Revision ID: e4f77g8h9i0d
Revises: d3e66f7g8h9c
Create Date: 2026-08-14 18:22:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e4f77g8h9i0d'
down_revision: Union[str, None] = 'd3e66f7g8h9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delete any old auto-generated fake pattern emails from the contacts table
    op.execute("""
        DELETE FROM contacts
        WHERE source = 'DISCOVERED'
          AND (
            email ILIKE 'careers@%'
            OR email ILIKE 'recruiting@%'
            OR email ILIKE 'jobs@%'
            OR email ILIKE 'hiring@%'
            OR email ILIKE 'talent@%'
          )
    """)


def downgrade() -> None:
    # Data cleanup operation — cannot be automatically reversed
    pass
