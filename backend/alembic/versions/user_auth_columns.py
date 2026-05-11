"""add user auth columns

Revision ID: userauth001
Revises: kb001
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa


revision = "userauth001"
down_revision = "kb001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("username", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
    op.execute("UPDATE users SET username = CONCAT('legacy_user_', id) WHERE username IS NULL")
    op.execute("UPDATE users SET password_hash = 'legacy-disabled' WHERE password_hash IS NULL")
    op.alter_column("users", "username", existing_type=sa.String(length=64), nullable=False)
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade():
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")