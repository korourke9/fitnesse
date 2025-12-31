"""User profile model for storing user attributes and facts."""
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, JSON, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserProfile(Base):
    """
    User profile model.
    
    Stores factual attributes about the user
    
    The additional_context field is a flexible JSON field for information
    the AI model discovers during conversation that may be useful for
    recommendations but wasn't part of the original schema.
    """
    __tablename__ = "user_profiles"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    
    # Biometric information
    height_cm = Column(Float, nullable=True)  # Height in centimeters
    weight_kg = Column(Float, nullable=True)  # Weight in kilograms
    age = Column(Integer, nullable=True)
    sex = Column(String, nullable=True)  # Using String for inclusivity
    
    # Lifestyle information
    activity_level = Column(Float, nullable=True)  # 0.0 (sedentary) to 1.0 (pro athlete), model estimates based on conversation
    dietary_preferences = Column(JSON, nullable=True)  # Array of preferences: ["vegetarian", "gluten-free", etc.]
    workout_preferences = Column(JSON, nullable=True)  # Array of constraints/preferences: ["no_running", "no_bike_access", "prefer_weights", etc.]
    conditions = Column(JSON, nullable=True)  # Array of medical/health conditions: ["diabetes", "knee_injury", "asthma", etc.]
    cooking_time_per_day_minutes = Column(Integer, nullable=True)
    meal_prep_preference = Column(String, nullable=True)  # e.g., "daily", "weekly", "no_prep"
    budget_per_week_usd = Column(Float, nullable=True)
    
    # Flexible field for AI-discovered context
    # This allows the model to store information it determines is useful
    # but wasn't part of the original schema (e.g., "works night shifts", 
    # "has food allergies to shellfish", "prefers spicy food")
    additional_context = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="profile")

