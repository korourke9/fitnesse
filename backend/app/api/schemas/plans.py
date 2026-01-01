"""Plan generation schemas."""
from typing import Optional, Dict, Any
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


