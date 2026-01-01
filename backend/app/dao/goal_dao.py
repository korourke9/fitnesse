"""Goal Data Access Object."""
from typing import List
from sqlalchemy.orm import Session

from app.models.goal import Goal


class GoalDAO:
    """Data access object for Goal operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_active_goals(self, user_id: str) -> List[Goal]:
        """Get active goals for a user."""
        return (
            self.db.query(Goal)
            .filter(Goal.user_id == user_id, Goal.is_active == True)  # noqa: E712
            .all()
        )


