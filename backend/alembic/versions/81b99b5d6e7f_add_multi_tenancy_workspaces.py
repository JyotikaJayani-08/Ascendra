"""add multi-tenancy workspaces

Revision ID: 81b99b5d6e7f
Revises: 80a98b4c5d6e
Create Date: 2026-07-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '81b99b5d6e7f'
down_revision: Union[str, None] = '80a98b4c5d6e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspaces_id'), 'workspaces', ['id'], unique=False)
    op.create_index(op.f('ix_workspaces_slug'), 'workspaces', ['slug'], unique=True)

    # 2. Create workspace_roles enum
    workspace_role_enum = postgresql.ENUM('OWNER', 'ADMIN', 'MEMBER', name='workspace_role', create_type=False)
    op.execute("DO $$ BEGIN CREATE TYPE workspace_role AS ENUM ('OWNER', 'ADMIN', 'MEMBER'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # 3. Create workspace_members table
    op.create_table(
        'workspace_members',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('workspace_id', sa.String(length=36), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('role', workspace_role_enum, nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_workspace_members_id'), 'workspace_members', ['id'], unique=False)
    op.create_index(op.f('ix_workspace_members_user_id'), 'workspace_members', ['user_id'], unique=False)
    op.create_index(op.f('ix_workspace_members_workspace_id'), 'workspace_members', ['workspace_id'], unique=False)

    # 4. Add workspace_id to core tables
    tables = [
        'applications', 'jobs', 'resumes', 'resume_versions', 
        'contacts', 'conversations', 'messages', 'follow_ups', 
        'notes', 'notifications', 'audit_logs'
    ]
    
    for table in tables:
        op.add_column(table, sa.Column('workspace_id', sa.String(length=36), nullable=True))
        op.create_index(op.f(f'ix_{table}_workspace_id'), table, ['workspace_id'], unique=False)
        op.create_foreign_key(f'fk_{table}_workspace_id', table, 'workspaces', ['workspace_id'], ['id'], ondelete='CASCADE')


def downgrade() -> None:
    tables = [
        'audit_logs', 'notifications', 'notes', 'follow_ups', 
        'messages', 'conversations', 'contacts', 'resume_versions', 
        'resumes', 'jobs', 'applications'
    ]
    
    for table in tables:
        op.drop_constraint(f'fk_{table}_workspace_id', table, type_='foreignkey')
        op.drop_index(op.f(f'ix_{table}_workspace_id'), table_name=table)
        op.drop_column(table, 'workspace_id')

    op.drop_index(op.f('ix_workspace_members_workspace_id'), table_name='workspace_members')
    op.drop_index(op.f('ix_workspace_members_user_id'), table_name='workspace_members')
    op.drop_index(op.f('ix_workspace_members_id'), table_name='workspace_members')
    op.drop_table('workspace_members')
    
    workspace_role_enum = postgresql.ENUM('OWNER', 'ADMIN', 'MEMBER', name='workspace_role')
    workspace_role_enum.drop(op.get_bind())

    op.drop_index(op.f('ix_workspaces_slug'), table_name='workspaces')
    op.drop_index(op.f('ix_workspaces_id'), table_name='workspaces')
    op.drop_table('workspaces')
