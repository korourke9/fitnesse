"""Plan Data Access Object."""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.plan import Plan, PlanType


class PlanDAO:
    """Data access object for Plan operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_active_plan(self, user_id: str, plan_type: PlanType) -> Optional[Plan]:
        """Get the active plan for a user and type."""
        return (
            self.db.query(Plan)
            .filter(
                Plan.user_id == user_id,
                Plan.plan_type == plan_type,
                Plan.is_active == True,  # noqa: E712
            )
            .first()
        )


