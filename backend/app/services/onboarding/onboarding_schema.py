"""Pydantic schemas for onboarding agent structured outputs."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ProfileData(BaseModel):
    """User profile data extracted from conversation."""
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    age: Optional[int] = None
    sex: Optional[str] = None
    activity_level: Optional[float] = Field(None, ge=0.0, le=1.0, description="Activity level from 0.0 (sedentary) to 1.0 (pro athlete)")
    dietary_preferences: Optional[List[str]] = None
    workout_preferences: Optional[List[str]] = None
    conditions: Optional[List[str]] = None
    cooking_time_per_day_minutes: Optional[int] = None
    meal_prep_preference: Optional[str] = None
    budget_per_week_usd: Optional[float] = None
    additional_context: Optional[Dict[str, Any]] = None


class GoalData(BaseModel):
    """Goal data extracted from conversation."""
    id: Optional[str] = Field(None, description="ID of existing goal to update. Omit for new goals.")
    goal_type: str = Field(..., description="Type of goal (weight_loss, muscle_gain, etc.)")
    description: str = Field(..., description="Description of the goal")
    target: str = Field(..., description="What is being targeted (e.g., 'weight', 'body fat percentage')")
    target_value: Optional[float] = None
    target_date: Optional[str] = Field(None, description="Target date in YYYY-MM-DD format")
    success_metrics: Optional[Dict[str, Any]] = None
    is_active: bool = Field(True, description="Set to false to mark goal as inactive/removed")


class ExtractedData(BaseModel):
    """Data extracted from conversation."""
    profile: Optional[ProfileData] = None
    goals: Optional[List[GoalData]] = Field(
        None,
        description="All user goals after processing this conversation. Include existing goals (with their id) that should be updated, new goals (without id), and mark goals for removal with is_active: false. Return the complete set of goals the user should have."
    )


class OnboardingResponse(BaseModel):
    """Structured response from onboarding agent."""
    response: str = Field(..., description="Your conversational response to the user (2-3 sentences, friendly and natural)")
    extracted_data: Optional[ExtractedData] = None
    is_complete: bool = Field(
        False,
        description="Set to true when onboarding is complete. Onboarding is complete when you have sufficient information to create a personalized plan (goals, basic biometrics, lifestyle constraints). You can ask the user if they want to provide more info, but if they indicate they're done or you have enough info, set this to true."
    )

