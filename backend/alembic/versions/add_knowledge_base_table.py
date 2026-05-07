"""add knowledge_base table

Revision ID: kb001
Revises: 
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'knowledge_base',
        sa.Column('id', sa.Integer, primary_key=True, index=True),
        sa.Column('module', sa.String(32), index=True),
        sa.Column('category', sa.String(32), index=True),
        sa.Column('keyword', sa.String(64), index=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('source', sa.String(128), default='builtin'),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
    )

def downgrade():
    op.drop_table('knowledge_base')
