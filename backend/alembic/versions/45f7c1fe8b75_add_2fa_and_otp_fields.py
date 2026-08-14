"""Add 2FA and OTP fields

Revision ID: 45f7c1fe8b75
Revises: 34e6b0ed7a64
Create Date: 2026-07-18 19:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '45f7c1fe8b75'
down_revision: Union[str, None] = '34e6b0ed7a64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to users
    op.add_column('users', sa.Column('verification_otp', sa.String(length=6), nullable=True))
    op.add_column('users', sa.Column('otp_expires_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('color_sequence', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('color_failures', sa.Integer(), server_default='0', nullable=False))

    # Add new columns to user_sessions
    op.add_column('user_sessions', sa.Column('last_2fa_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove columns from user_sessions
    op.drop_column('user_sessions', 'last_2fa_at')

    # Remove columns from users
    op.drop_column('users', 'color_failures')
    op.drop_column('users', 'color_sequence')
    op.drop_column('users', 'otp_expires_at')
    op.drop_column('users', 'verification_otp')
