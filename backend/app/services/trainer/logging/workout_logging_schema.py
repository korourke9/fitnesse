"""Pydantic schema for workout parsing outputs."""
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class ExerciseItem(BaseModel):
    name: str = Field(..., description="Exercise name, e.g. 'Bench Press', 'Running'")
    sets: Optional[int] = Field(None, ge=1, description="Number of sets")
    reps: Optional[str] = Field(None, description="Reps per set, e.g. '8-10', '12'")
    weight: Optional[str] = Field(None, description="Weight used, e.g. '135 lbs', 'bodyweight'")
    duration: Optional[str] = Field(None, description="Duration for cardio, e.g. '30 min', '5 miles'")
    notes: Optional[str] = Field(None, description="Additional notes about the exercise")


class WorkoutParseResult(BaseModel):
    normalized_text: str = Field(..., description="Normalized/cleaned workout description")
    exercises: List[ExerciseItem] = Field(default_factory=list)
    total_duration_minutes: Optional[float] = Field(None, ge=0, description="Total workout duration in minutes")
    estimated_calories_burned: Optional[float] = Field(None, ge=0, description="Estimated calories burned")
    confidence: float = Field(..., ge=0, le=1)
    questions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
