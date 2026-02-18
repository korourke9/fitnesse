"""Plan models for storing diet and exercise plans."""
import enum

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Date, Boolean, Integer, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PlanType(str, enum.Enum):
    """Plan type enumeration (one plan row per type)."""

    MEAL = "meal"
    WORKOUT = "workout"


class Plan(Base):
    """
    Plan model for storing a single type of plan (meal or workout).
    
    A plan represents a period of time (typically a month) with specific
    recommendations tailored to the user's goals and profile.
    """
    __tablename__ = "plans"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    # Store enum values ("meal", "workout") in the DB, not the member names.
    plan_type = Column(
        SQLEnum(
            PlanType,
            name="plantype",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        index=True,
    )
    
    # Plan metadata
    name = Column(String, nullable=True)  # e.g., "January 2024 Plan"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)  # Nullable - plans are ongoing until replaced
    duration_days = Column(Integer, nullable=True)  # Deprecated - kept for backwards compatibility
    
    # Plan content (stored as JSON for flexibility)
    # For MEAL plans, this is the diet plan object.
    # For WORKOUT plans, this is the exercise plan object.
    plan_data = Column(JSON, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="plans")
    plan_items = relationship("PlanItem", back_populates="plan", cascade="all, delete-orphan")


class PlanItem(Base):
    """
    PlanItem model for storing daily plan items (meals, workouts).
    
    Each item represents a specific meal or workout for a specific day
    within a plan.
    """
    __tablename__ = "plan_items"

    id = Column(String, primary_key=True, index=True)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=False, index=True)
    
    # Item metadata
    item_type = Column(String, nullable=False)  # "meal" or "workout"
    day_number = Column(Integer, nullable=False)  # Day 1, 2, 3, etc. within the plan
    date = Column(Date, nullable=False)  # Actual date for this item
    
    # Item content (stored as JSON for flexibility)
    # For meals: {
    #   "meal_name": "Breakfast",
    #   "description": "Oatmeal with berries and protein",
    #   "calories": 400,
    #   "macros": {"protein": 25, "carbs": 50, "fat": 10},
    #   "ingredients": ["oats", "berries", "protein powder"],
    #   "instructions": "Cook oats, add berries, mix in protein"
    # }
    # For workouts: {
    #   "workout_name": "Upper Body Strength",
    #   "description": "Focus on chest, back, and shoulders",
    #   "duration_minutes": 45,
    #   "exercises": [
    #     {"name": "Bench Press", "sets": 3, "reps": 8, "weight": "bodyweight"},
    #     ...
    #   ],
    #   "notes": "Focus on form"
    # }
    item_data = Column(JSON, nullable=False)
    
    # Status
    is_completed = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    plan = relationship("Plan", back_populates="plan_items")

