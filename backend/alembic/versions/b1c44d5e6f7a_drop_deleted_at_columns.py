"""drop deleted_at columns from all tables

Revision ID: b1c44d5e6f7a
Revises: 3e9706e9cf16
Create Date: 2026-08-13 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1c44d5e6f7a'
down_revision: Union[str, None] = '3e9706e9cf16'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tables that have deleted_at, verified against migration history:
#   79e17a3f2187: ai_generations, applications, companies, contacts,
#                 conversations, follow_ups, jobs, messages, notifications,
#                 resume_versions, resumes, users  + audit_logs (created with it)
#   dbbd9e326dc0: notes (re-created with it)
#   93d11d7f8g9h: workspaces, workspace_members
#   a5f33g8h1i2j: user_email_configs (created with it)
_tables_with_deleted_at = [
    'users',
    'applications',
    'jobs',
    'resumes',
    'resume_versions',
    'conversations',
    'messages',
    'follow_ups',
    'contacts',
    'companies',
    'notifications',
    'ai_generations',
    'audit_logs',
    'workspaces',
    'workspace_members',
    'user_email_configs',
    'notes',
]


def upgrade() -> None:
    # Use raw SQL with IF EXISTS to safely drop columns that may or may not exist.
    # This avoids PostgreSQL aborting the transaction on a failed DDL statement.
    for table in _tables_with_deleted_at:
        op.execute(
            f"ALTER TABLE public.{table} DROP COLUMN IF EXISTS deleted_at;"
        )


def downgrade() -> None:
    for table in _tables_with_deleted_at:
        op.add_column(
            table,
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )
