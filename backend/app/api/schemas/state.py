"""State-related schemas."""
from datetime import date
from typing import Optional, Dict, Any

from pydantic import BaseModel


class PlanSummary(BaseModel):
    """Minimal plan summary exposed to the UI."""

    start_date: Optional[date] = None
    end_date: Optional[date] = None
    duration_days: Optional[int] = None
    daily_calories: Optional[float] = None
    macros: Optional[Dict[str, Any]] = None
    workouts_per_week: Optional[int] = None
    notes: Optional[str] = None


class SectionState(BaseModel):
    has_plan: bool
    plan_id: Optional[str] = None
    summary: Optional[PlanSummary] = None


class AppStateResponse(BaseModel):
    user_id: str
    onboarding_complete: bool
    nutrition: SectionState
    training: SectionState


