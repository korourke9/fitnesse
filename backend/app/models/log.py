"""Unified logging model (meals, workouts, goal check-ins, etc.)."""
import enum
import uuid

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Enum as SQLEnum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class LogType(str, enum.Enum):
    MEAL = "meal"
    WORKOUT = "workout"
    GOAL_CHECKIN = "goal_checkin"


class Log(Base):
    """Stores a logged entry for a user, typed by `log_type` with JSON payloads."""

    __tablename__ = "logs"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)

    # Store enum values ("meal", "workout", "goal_checkin") in the DB, not the member names.
    log_type = Column(
        SQLEnum(
            LogType,
            name="logtype",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        index=True,
    )

    # Common free-text input (e.g. meal description, check-in note)
    raw_text = Column(Text, nullable=False)

    # Optional structured payloads (meaning depends on `log_type`)
    parsed_data = Column(JSON, nullable=True)
    confirmed_data = Column(JSON, nullable=True)
    details = Column(JSON, nullable=True)

    logged_at = Column(DateTime(timezone=True), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="logs")


