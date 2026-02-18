"""unify_logs

Revision ID: 773fb4688df8
Revises: 02c332a04105
Create Date: 2026-02-13 11:25:30.529466

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '773fb4688df8'
down_revision = '02c332a04105'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create the unified logs table
    op.create_table('logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('log_type', sa.Enum('meal', 'workout', 'goal_checkin', name='logtype'), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('parsed_data', sa.JSON(), nullable=True),
        sa.Column('confirmed_data', sa.JSON(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('logged_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_logs_id'), 'logs', ['id'], unique=False)
    op.create_index(op.f('ix_logs_user_id'), 'logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_logs_log_type'), 'logs', ['log_type'], unique=False)

    # Migrate data from meal_logs
    op.execute("""
        INSERT INTO logs (id, user_id, log_type, raw_text, parsed_data, confirmed_data, logged_at, created_at, updated_at)
        SELECT id, user_id, 'meal', raw_text, parsed_data, confirmed_data, logged_at, created_at, updated_at
        FROM meal_logs
    """)

    # Migrate data from goal_checkins (text -> raw_text, metrics -> details)
    op.execute("""
        INSERT INTO logs (id, user_id, log_type, raw_text, details, logged_at, created_at, updated_at)
        SELECT id, user_id, 'goal_checkin', text, metrics, logged_at, created_at, updated_at
        FROM goal_checkins
    """)

    # Drop old tables
    op.drop_index(op.f('ix_meal_logs_user_id'), table_name='meal_logs')
    op.drop_index(op.f('ix_meal_logs_id'), table_name='meal_logs')
    op.drop_table('meal_logs')
    
    op.drop_index(op.f('ix_goal_checkins_user_id'), table_name='goal_checkins')
    op.drop_index(op.f('ix_goal_checkins_id'), table_name='goal_checkins')
    op.drop_table('goal_checkins')


def downgrade() -> None:
    # Recreate old tables
    op.create_table('meal_logs',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('raw_text', sa.String(), nullable=False),
        sa.Column('parsed_data', sa.JSON(), nullable=True),
        sa.Column('confirmed_data', sa.JSON(), nullable=False),
        sa.Column('logged_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_meal_logs_id'), 'meal_logs', ['id'], unique=False)
    op.create_index(op.f('ix_meal_logs_user_id'), 'meal_logs', ['user_id'], unique=False)

    op.create_table('goal_checkins',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('logged_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_goal_checkins_id'), 'goal_checkins', ['id'], unique=False)
    op.create_index(op.f('ix_goal_checkins_user_id'), 'goal_checkins', ['user_id'], unique=False)

    # Migrate data back (only meal and goal_checkin types)
    op.execute("""
        INSERT INTO meal_logs (id, user_id, raw_text, parsed_data, confirmed_data, logged_at, created_at, updated_at)
        SELECT id, user_id, raw_text, parsed_data, confirmed_data, logged_at, created_at, updated_at
        FROM logs
        WHERE log_type = 'meal'
    """)

    op.execute("""
        INSERT INTO goal_checkins (id, user_id, text, metrics, logged_at, created_at, updated_at)
        SELECT id, user_id, raw_text, details, logged_at, created_at, updated_at
        FROM logs
        WHERE log_type = 'goal_checkin'
    """)

    # Drop unified logs table
    op.drop_index(op.f('ix_logs_log_type'), table_name='logs')
    op.drop_index(op.f('ix_logs_user_id'), table_name='logs')
    op.drop_index(op.f('ix_logs_id'), table_name='logs')
    op.drop_table('logs')
    
    # Drop the enum type
    op.execute("DROP TYPE IF EXISTS logtype")

