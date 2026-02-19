"""Plan generation and view schemas."""
from typing import Optional, Dict, Any, List, Literal, Union, Annotated
from datetime import date

from pydantic import BaseModel, Field, Discriminator

from app.services.nutritionist.planning.meal_plan_schema import MacroEstimate


class PlanGenerateRequest(BaseModel):
    duration_days: int = Field(30, ge=7, le=90)


class PlanGenerateSummary(BaseModel):
    plan_id: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: Optional[int] = None
    data: Dict[str, Any] = Field(default_factory=dict)


# Plan view (today) response - flexible shape for meal vs workout
class PlanViewTargets(BaseModel):
    daily_calories: Optional[float] = None
    macros: Optional[Dict[str, Any]] = None


class PlanViewMeal(BaseModel):
    meal_type: str
    name: str
    nutrition: Optional[MacroEstimate] = None
    ingredients: Optional[List[str]] = None
    instructions: Optional[str] = None


class PlanViewStrengthExercise(BaseModel):
    exercise_type: Literal["strength"] = "strength"
    name: str
    sets: int
    reps: str
    weight: str
    notes: Optional[str] = None


class PlanViewCardioExercise(BaseModel):
    exercise_type: Literal["cardio"] = "cardio"
    name: str
    duration: str
    distance: Optional[str] = None
    intensity: str
    notes: Optional[str] = None


class PlanViewFlexibilityExercise(BaseModel):
    exercise_type: Literal["flexibility"] = "flexibility"
    name: str
    duration: str
    notes: Optional[str] = None


PlanViewExerciseDetail = Annotated[
    Union[PlanViewStrengthExercise, PlanViewCardioExercise, PlanViewFlexibilityExercise],
    Discriminator("exercise_type"),
]


class PlanViewWorkout(BaseModel):
    type: str
    description: str


class PlanViewResponse(BaseModel):
    date: str
    plan_type: str
    targets: Optional[PlanViewTargets] = None
    meals: Optional[List[PlanViewMeal]] = []
    workout: Optional[PlanViewWorkout] = None
    exercises: Optional[List[str]] = []
    exercise_details: Optional[List[PlanViewExerciseDetail]] = None


