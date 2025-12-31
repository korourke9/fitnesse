"""Pydantic schemas for coordination agent structured outputs."""
from typing import Optional
from pydantic import BaseModel, Field


class CoordinationResponse(BaseModel):
    """Structured response from coordination agent."""
    response: str = Field(..., description="Your conversational response to the user (2-3 sentences, friendly and natural)")
    suggested_agent: Optional[str] = Field(
        None,
        description="The agent the user should interact with next. Options: 'nutritionist', 'trainer', or None if staying with coordination. Only suggest an agent if the user explicitly wants to interact with one or if it's clear from context."
    )
    action: Optional[str] = Field(
        None,
        description="""Action to take:
        - 'generate_meal_plan': Generate the user's personalized meal plan
        - 'generate_workout_plan': Generate the user's personalized workout plan
        - 'route_to_nutritionist': Route to nutritionist for meal logging (use if they already have a meal plan)
        - 'route_to_trainer': Route to trainer for exercise logging (use if they already have a workout plan)
        - 'show_meal_plan': Show the user's meal plan
        - 'show_workout_plan': Show the user's workout plan
        - 'stay_here': Stay with coordination for general questions
        - None: No specific action needed"""
    )

