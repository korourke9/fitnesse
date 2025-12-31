"""Goal model for storing user objectives and success metrics."""
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Date, Boolean, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class GoalType(str, enum.Enum):
    """Goal type enumeration."""
    WEIGHT_LOSS = "weight_loss"
    WEIGHT_GAIN = "weight_gain"
    MUSCLE_GAIN = "muscle_gain"
    ENDURANCE = "endurance"
    GENERAL_FITNESS = "general_fitness"
    FLEXIBILITY = "flexibility"
    NUTRITION = "nutrition"
    BODY_FAT_PERCENTAGE = "body_fat_percentage"
    LONGEVITY = "longevity"
    OTHER = "other"


class Goal(Base):
    """
    Goal model.
    
    Represents what the user wants to achieve and how they measure success.
    This is different from UserProfile, which stores who they are.
    
    A user can have multiple goals. Goals can be active or completed.
    
    The target system is flexible:
    - target (required): Describes what they're targeting (e.g., "body fat percentage", 
      "weight", "5k time", "bench press")
    - target_value (optional): The numeric value they want to achieve (e.g., 15.0 for 
      body fat %, 180 for weight in lbs, 25 for 5k time in minutes)
    
    Success metrics are stored as JSON to allow additional flexibility in how success
    is measured (e.g., {"primary": "lose_weight", "target_kg": 5, "timeframe_weeks": 12}).
    """
    __tablename__ = "goals"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Goal information
    goal_type = Column(SQLEnum(GoalType), nullable=False)
    description = Column(Text, nullable=False)  # Free-form description of the goal
    
    # Flexible target system
    # target: Required - describes what they're targeting (e.g., "body fat percentage", "weight", "5k time", "bench press")
    target = Column(String, nullable=False)
    # target_value: Optional - the numeric value they want to achieve (e.g., 15.0 for body fat %, 180 for weight in lbs)
    target_value = Column(Float, nullable=True)
    target_date = Column(Date, nullable=True)  # When they want to achieve this
    
    # Success metrics - flexible JSON structure
    # Examples:
    # {"primary": "lose_weight", "target_kg": 5, "timeframe_weeks": 12}
    # {"primary": "run_5k", "target_time_minutes": 25}
    # {"primary": "eat_vegetables", "servings_per_day": 5}
    success_metrics = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="goals")

