"""fix supabase rls linter errors and warnings

Revision ID: 94e22e8g9h0i
Revises: 93d11d7f8g9h
Create Date: 2026-07-30 13:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '94e22e8g9h0i'
down_revision: Union[str, None] = '93d11d7f8g9h'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

all_tables = [
    'applications', 'jobs', 'resumes', 'resume_versions', 
    'contacts', 'conversations', 'messages', 'follow_ups', 
    'notes', 'notifications', 'audit_logs', 'workspaces', 'workspace_members'
]

def upgrade() -> None:
    # 1. Enable RLS on all public tables to fix 'rls_disabled_in_public' and 'policy_exists_rls_disabled'
    for table in all_tables:
        op.execute(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY;")

    # 2. Re-create workspace policies using (SELECT auth.uid()) for O(1) query performance InitPlan
    workspace_tables = [
        'applications', 'jobs', 'resumes', 'resume_versions', 
        'contacts', 'conversations', 'messages', 'follow_ups', 
        'notes', 'notifications', 'audit_logs'
    ]

    for table in workspace_tables:
        op.execute(f"""
            DO $$
            BEGIN
                EXECUTE 'DROP POLICY IF EXISTS "Workspace members can access {table}" ON public.{table}';
                EXECUTE 'CREATE POLICY "Workspace members can access {table}" ON public.{table} FOR ALL USING (workspace_id IN (SELECT workspace_id FROM public.workspace_members WHERE user_id = (SELECT auth.uid())))';
            EXCEPTION WHEN OTHERS THEN
                NULL;
            END $$;
        """)

    # 3. Add explicit policies for workspaces and workspace_members
    op.execute("""
        DO $$
        BEGIN
            EXECUTE 'DROP POLICY IF EXISTS "Workspace members can access workspaces" ON public.workspaces';
            EXECUTE 'CREATE POLICY "Workspace members can access workspaces" ON public.workspaces FOR ALL USING (id IN (SELECT workspace_id FROM public.workspace_members WHERE user_id = (SELECT auth.uid())));';
            
            EXECUTE 'DROP POLICY IF EXISTS "Members can access workspace_members" ON public.workspace_members';
            EXECUTE 'CREATE POLICY "Members can access workspace_members" ON public.workspace_members FOR ALL USING (user_id = (SELECT auth.uid()) OR workspace_id IN (SELECT workspace_id FROM public.workspace_members WHERE user_id = (SELECT auth.uid())));';
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END $$;
    """)

def downgrade() -> None:
    for table in all_tables:
        op.execute(f"ALTER TABLE public.{table} DISABLE ROW LEVEL SECURITY;")
