"""add_plan_type_and_split_plans

Revision ID: 1efcfd6c5239
Revises: 04cad26378fd
Create Date: 2026-01-01 13:55:23.933832

"""
from alembic import op
import sqlalchemy as sa
import uuid


# revision identifiers, used by Alembic.
revision = '1efcfd6c5239'
down_revision = '04cad26378fd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add plan_type as nullable first to allow data migration
    plan_type_enum = sa.Enum('meal', 'workout', name='plantype')
    plan_type_enum.create(op.get_bind(), checkfirst=True)

    op.add_column('plans', sa.Column('plan_type', plan_type_enum, nullable=True))

    # Data migration: split existing combined plan_data into per-type rows
    conn = op.get_bind()

    plans = sa.table(
        "plans",
        sa.column("id", sa.String),
        sa.column("user_id", sa.String),
        sa.column("plan_type", sa.String),
        sa.column("name", sa.String),
        sa.column("start_date", sa.Date),
        sa.column("end_date", sa.Date),
        sa.column("duration_days", sa.Integer),
        sa.column("plan_data", sa.JSON),
        sa.column("is_active", sa.Boolean),
        sa.column("is_completed", sa.Boolean),
    )

    rows = conn.execute(
        sa.text(
            """
            SELECT id, user_id, name, start_date, end_date, duration_days, plan_data, is_active, is_completed
            FROM plans
            """
        )
    ).mappings().all()

    for row in rows:
        plan_id = row["id"]
        plan_data = row["plan_data"]

        # Some DBs may return JSON as string; attempt to parse if needed
        if isinstance(plan_data, str):
            try:
                import json
                plan_data = json.loads(plan_data)
            except Exception:
                plan_data = {}

        diet = plan_data.get("diet") if isinstance(plan_data, dict) else None
        exercise = plan_data.get("exercise") if isinstance(plan_data, dict) else None

        # If both exist, reuse existing row for meal plan, insert a new workout plan row
        if diet and exercise:
            conn.execute(
                sa.update(plans)
                .where(plans.c.id == plan_id)
                .values(plan_type="meal", plan_data=diet)
            )

            new_id = str(uuid.uuid4())
            new_name = (row["name"] or "Plan") + " (Workout)"
            conn.execute(
                sa.insert(plans).values(
                    id=new_id,
                    user_id=row["user_id"],
                    plan_type="workout",
                    name=new_name,
                    start_date=row["start_date"],
                    end_date=row["end_date"],
                    duration_days=row["duration_days"],
                    plan_data=exercise,
                    is_active=row["is_active"],
                    is_completed=row["is_completed"],
                )
            )

        # If only diet exists, repurpose existing row
        elif diet:
            conn.execute(
                sa.update(plans)
                .where(plans.c.id == plan_id)
                .values(plan_type="meal", plan_data=diet)
            )

        # If only exercise exists, repurpose existing row
        elif exercise:
            conn.execute(
                sa.update(plans)
                .where(plans.c.id == plan_id)
                .values(plan_type="workout", plan_data=exercise)
            )

        # Otherwise set a default type to satisfy NOT NULL (empty/legacy plan shell)
        else:
            conn.execute(
                sa.update(plans)
                .where(plans.c.id == plan_id)
                .values(plan_type="meal")
            )

    # Enforce non-null plan_type + index
    op.alter_column('plans', 'plan_type', nullable=False)
    op.create_index(op.f('ix_plans_plan_type'), 'plans', ['plan_type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_plans_plan_type'), table_name='plans')
    op.drop_column('plans', 'plan_type')
    # Best-effort enum cleanup for Postgres (safe to ignore if unsupported)
    try:
        op.execute("DROP TYPE IF EXISTS plantype")
    except Exception:
        pass

