"""Goal check-in logging model."""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class GoalCheckIn(Base):
    """Stores a user check-in related to their goals."""

    __tablename__ = "goal_checkins"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    text = Column(Text, nullable=False)
    metrics = Column(JSON, nullable=True)  # optional structured metrics later
    logged_at = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="goal_checkins")


