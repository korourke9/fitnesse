"""make plan end_date nullable

Revision ID: a2b3c4d5e6f7
Revises: 773fb4688df8
Create Date: 2026-02-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2b3c4d5e6f7'
down_revision = '773fb4688df8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Make end_date nullable - plans are now ongoing until replaced
    op.alter_column('plans', 'end_date',
                    existing_type=sa.Date(),
                    nullable=True)


def downgrade() -> None:
    # Revert: make end_date required again
    # Note: This will fail if there are NULL values - would need to set them first
    op.alter_column('plans', 'end_date',
                    existing_type=sa.Date(),
                    nullable=False)
