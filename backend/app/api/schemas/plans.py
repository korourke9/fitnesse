"""Plan generation and view schemas."""
from typing import Optional, Dict, Any, List
from datetime import date

from pydantic import BaseModel, Field


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
    nutrition: Optional[Dict[str, Any]] = None


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


