"""update rls for workspaces

Revision ID: 92c00c6e7f8g
Revises: 81b99b5d6e7f
Create Date: 2026-07-28 12:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '92c00c6e7f8g'
down_revision: Union[str, None] = '81b99b5d6e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

tables_to_update = [
    'applications', 'jobs', 'resumes', 'resume_versions', 
    'contacts', 'conversations', 'messages', 'follow_ups', 
    'notes', 'notifications', 'audit_logs'
]

def upgrade() -> None:
    # Drop old user-based policies and create new workspace-based policies
    for table in tables_to_update:
        op.execute(f"""
            DO $$
            BEGIN
                EXECUTE 'DROP POLICY IF EXISTS "Users can manage their own {table}" ON public.{table}';
                EXECUTE 'DROP POLICY IF EXISTS "Users can view their own {table}" ON public.{table}';
                
                -- Create workspace policy: user can access row if they are in the workspace
                EXECUTE 'CREATE POLICY "Workspace members can access {table}" ON public.{table} FOR ALL USING (workspace_id IN (SELECT workspace_id FROM public.workspace_members WHERE user_id = auth.uid()))';
            EXCEPTION WHEN OTHERS THEN
                NULL;
            END $$;
        """)

def downgrade() -> None:
    # Downgrade is best-effort since we destroyed the old policies
    for table in tables_to_update:
        op.execute(f"""
            DO $$
            BEGIN
                EXECUTE 'DROP POLICY IF EXISTS "Workspace members can access {table}" ON public.{table}';
            EXCEPTION WHEN OTHERS THEN
                NULL;
            END $$;
        """)

