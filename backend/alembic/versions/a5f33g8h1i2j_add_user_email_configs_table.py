"""add user_email_configs table

Revision ID: a5f33g8h1i2j
Revises: 94e22e8g9h0i
Create Date: 2026-07-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a5f33g8h1i2j'
down_revision: Union[str, None] = '94e22e8g9h0i'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create email_provider_type enum
    email_provider_type = postgresql.ENUM(
        'SMTP', 'GMAIL_OAUTH', 'OUTLOOK_OAUTH',
        name='email_provider_type',
        create_type=False,
    )
    email_provider_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'user_email_configs',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            'provider_type',
            postgresql.ENUM('SMTP', 'GMAIL_OAUTH', 'OUTLOOK_OAUTH', name='email_provider_type', create_type=False),
            nullable=False,
        ),
        sa.Column('smtp_host', sa.String(255), nullable=False, server_default='smtp.gmail.com'),
        sa.Column('smtp_port', sa.Integer(), nullable=False, server_default='587'),
        sa.Column('smtp_username', sa.String(320), nullable=False),
        sa.Column('smtp_password', sa.String(512), nullable=False),
        sa.Column('display_name', sa.String(255), nullable=True),
        sa.Column('is_default', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_email_configs_user_id', 'user_email_configs', ['user_id'])

    # Enable RLS on the new table
    op.execute("ALTER TABLE user_email_configs ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE user_email_configs FORCE ROW LEVEL SECURITY;")


def downgrade() -> None:
    op.execute("ALTER TABLE user_email_configs DISABLE ROW LEVEL SECURITY;")
    op.drop_index('ix_user_email_configs_user_id', table_name='user_email_configs')
    op.drop_table('user_email_configs')
    # Don't drop the enum type — it may be referenced elsewhere
