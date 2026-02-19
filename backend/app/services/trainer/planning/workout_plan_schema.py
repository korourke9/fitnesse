"""Workout plan schema - canonical structure for workout plan content.

Plans are stored as JSON in Plan.plan_data.

Exercise detail types (StrengthExerciseDetail, CardioExerciseDetail,
FlexibilityExerciseDetail, ExerciseDetail) are shared with workout logging.
"""
from typing import Any, Dict, List, Optional, Literal, Union, Annotated

from pydantic import BaseModel, Field, Discriminator


class StrengthExerciseDetail(BaseModel):
    """Details for a strength training exercise."""
    exercise_type: Literal["strength"] = "strength"
    name: str
    sets: int
    reps: str  # e.g. "10-12", "8-10", "AMRAP"
    weight: str  # e.g. "bodyweight", "10kg", "moderate"
    notes: Optional[str] = None


class CardioExerciseDetail(BaseModel):
    """Details for a cardio/endurance exercise."""
    exercise_type: Literal["cardio"] = "cardio"
    name: str
    duration: str  # e.g. "30 minutes", "45 min"
    distance: Optional[str] = None  # e.g. "6 miles", "5km", "10k" (optional - some cardio is time-based)
    intensity: str  # e.g. "moderate pace", "easy run", "8:00/mile", "Zone 2"
    notes: Optional[str] = None


class FlexibilityExerciseDetail(BaseModel):
    """Details for flexibility/mobility exercises."""
    exercise_type: Literal["flexibility"] = "flexibility"
    name: str
    duration: str  # e.g. "5 minutes", "hold for 30 seconds"
    notes: Optional[str] = None


# Union type for exercise details - discriminated by exercise_type field
ExerciseDetail = Annotated[
    Union[StrengthExerciseDetail, CardioExerciseDetail, FlexibilityExerciseDetail],
    Discriminator("exercise_type"),
]


class DayWorkout(BaseModel):
    """One day in the weekly workout schedule (day 1 = Monday .. 7 = Sunday)."""
    day: int = Field(..., ge=1, le=7)
    type: str = "Rest"
    description: str = ""
    exercises: List[str] = Field(default_factory=list)  # Simple list for basic view
    exercise_details: Optional[List[ExerciseDetail]] = None  # Full details when expanded


class WorkoutPlanData(BaseModel):
    """Canonical workout plan content. Always has weekly_schedule (7 days)."""
    workouts_per_week: Optional[int] = None
    workout_duration_minutes: Optional[int] = None
    focus_areas: List[str] = Field(default_factory=list)
    guidelines: List[str] = Field(default_factory=list)
    sample_exercises: Dict[str, List[str]] = Field(default_factory=dict)
    notes: Optional[str] = None
    weekly_schedule: List[DayWorkout] = Field(default_factory=list)

    @classmethod
    def from_stored(cls, data: Any) -> "WorkoutPlanData":
        """Build from DB plan_data. Expects canonical JSON (raises ValidationError if invalid)."""
        return cls.model_validate(data)
