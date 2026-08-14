"""add audit columns to workspaces

Revision ID: 93d11d7f8g9h
Revises: 92c00c6e7f8g
Create Date: 2026-07-29 11:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '93d11d7f8g9h'
down_revision: Union[str, None] = '92c00c6e7f8g'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Add audit columns to workspaces
    op.add_column('workspaces', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('workspaces', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('workspaces', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    
    # Add audit columns to workspace_members
    op.add_column('workspace_members', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('workspace_members', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False))
    op.add_column('workspace_members', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

def downgrade() -> None:
    op.drop_column('workspace_members', 'deleted_at')
    op.drop_column('workspace_members', 'updated_at')
    op.drop_column('workspace_members', 'created_at')
    
    op.drop_column('workspaces', 'deleted_at')
    op.drop_column('workspaces', 'updated_at')
    op.drop_column('workspaces', 'created_at')
