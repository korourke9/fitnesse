"""Pydantic schema for workout parsing outputs.

Uses the same exercise detail types as the workout plan schema so planned
and logged workouts share a single canonical shape (strength / cardio / flexibility).
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.services.trainer.planning.workout_plan_schema import (
    StrengthExerciseDetail,
    CardioExerciseDetail,
    FlexibilityExerciseDetail,
    ExerciseDetail,
)


class WorkoutParseResult(BaseModel):
    """Structured result of parsing a workout description."""

    normalized_text: str = Field(
        ..., description="Normalized/cleaned workout description"
    )
    exercises: List[ExerciseDetail] = Field(
        default_factory=list,
        description="Exercises with type-specific details (strength, cardio, or flexibility)",
    )
    total_duration_minutes: Optional[float] = Field(
        None, ge=0, description="Total workout duration in minutes"
    )
    estimated_calories_burned: Optional[float] = Field(
        None, ge=0, description="Estimated calories burned"
    )
    confidence: float = Field(..., ge=0, le=1)
    questions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Re-export for consumers that need the exercise types
__all__ = [
    "WorkoutParseResult",
    "ExerciseDetail",
    "StrengthExerciseDetail",
    "CardioExerciseDetail",
    "FlexibilityExerciseDetail",
]
