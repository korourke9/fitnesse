"""UserProfile Data Access Object."""
from typing import Optional
from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile


class UserProfileDAO:
    """Data access object for UserProfile operations."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_user_id(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by user_id."""
        return self.db.query(UserProfile).filter(UserProfile.user_id == user_id).first()


