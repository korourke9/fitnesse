"""add_new_agent_types


Revision ID: 0cffcbdae02d
Revises: c694110f0ea9
Create Date: 2025-12-30 21:14:44.571517

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0cffcbdae02d'
down_revision = 'c694110f0ea9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new agent types to the PostgreSQL enum
    # PostgreSQL requires ALTER TYPE to add new enum values
    op.execute("ALTER TYPE agenttype ADD VALUE IF NOT EXISTS 'COORDINATION'")
    op.execute("ALTER TYPE agenttype ADD VALUE IF NOT EXISTS 'NUTRITIONIST'")
    op.execute("ALTER TYPE agenttype ADD VALUE IF NOT EXISTS 'TRAINER'")
    op.execute("ALTER TYPE agenttype ADD VALUE IF NOT EXISTS 'ANALYTICS'")


def downgrade() -> None:
    # Note: PostgreSQL doesn't support removing enum values directly
    # Would need to recreate the enum type to remove values
    pass

