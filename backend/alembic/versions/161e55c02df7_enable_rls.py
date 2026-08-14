"""Enable RLS for Supabase PostgREST security

Revision ID: 161e55c02df7
Revises: 160e44b01ce6
Create Date: 2026-07-21 12:28:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '161e55c02df7'
down_revision: Union[str, None] = '160e44b01ce6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tables = [
    'alembic_version',
    'ai_generations',
    'jobs',
    'companies',
    'contacts',
    'notifications',
    'resumes',
    'resume_versions',
    'users',
    'applications',
    'conversations',
    'follow_ups',
    'messages'
]

def upgrade() -> None:
    for table in tables:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")

def downgrade() -> None:
    for table in tables:
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")
