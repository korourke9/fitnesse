"""Plan models for storing diet and exercise plans."""
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Date, Boolean, Text, Integer
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Plan(Base):
    """
    Plan model for storing user's diet and exercise plans.
    
    A plan represents a period of time (typically a month) with specific
    diet and exercise recommendations tailored to the user's goals and profile.
    """
    __tablename__ = "plans"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Plan metadata
    name = Column(String, nullable=True)  # e.g., "January 2024 Plan"
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_days = Column(Integer, nullable=False)  # Typically 30 days
    
    # Plan content (stored as JSON for flexibility)
    # Structure: {
    #   "diet": {
    #     "daily_calories": 2000,
    #     "macros": {"protein": 150, "carbs": 200, "fat": 65},
    #     "meals_per_day": 3,
    #     "guidelines": ["Eat protein with every meal", ...]
    #   },
    #   "exercise": {
    #     "workouts_per_week": 4,
    #     "workout_duration_minutes": 45,
    #     "focus_areas": ["strength", "cardio"],
    #     "guidelines": ["Rest day between strength sessions", ...]
    #   },
    #   "notes": "Custom notes from the AI about this plan"
    # }
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

