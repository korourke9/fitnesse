"""Plan Data Access Object."""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.plan import Plan, PlanType


class PlanDAO:
    """Data access object for Plan operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, plan_id: str, user_id: str) -> Optional[Plan]:
        """Get a plan by id if it belongs to the user."""
        return (
            self.db.query(Plan)
            .filter(Plan.id == plan_id, Plan.user_id == user_id)
            .first()
        )

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


