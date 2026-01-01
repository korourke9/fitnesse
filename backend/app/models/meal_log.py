"""Meal logging model."""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class MealLog(Base):
    """Stores a logged meal entry for a user."""

    __tablename__ = "meal_logs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    raw_text = Column(String, nullable=False)
    parsed_data = Column(JSON, nullable=True)
    confirmed_data = Column(JSON, nullable=False)

    logged_at = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="meal_logs")


