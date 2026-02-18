"""Logging API schemas."""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MealParseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    logged_at: Optional[datetime] = None


class MealParseResponse(BaseModel):
    parsed: Dict[str, Any]


class MealLogCreateRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=4000)
    parsed_data: Optional[Dict[str, Any]] = None
    confirmed_data: Dict[str, Any]
    logged_at: Optional[datetime] = None


class MealLogResponse(BaseModel):
    id: str
    raw_text: str
    confirmed_data: Dict[str, Any]
    logged_at: datetime

    class Config:
        from_attributes = True


class GoalCheckInCreateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    logged_at: Optional[datetime] = None


class GoalCheckInResponse(BaseModel):
    id: str
    text: str
    logged_at: datetime

    class Config:
        from_attributes = True


class WorkoutParseRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    logged_at: Optional[datetime] = None


class WorkoutParseResponse(BaseModel):
    parsed: Dict[str, Any]


class WorkoutLogCreateRequest(BaseModel):
    raw_text: str = Field(..., min_length=1, max_length=4000)
    parsed_data: Optional[Dict[str, Any]] = None
    confirmed_data: Dict[str, Any]
    logged_at: Optional[datetime] = None


class WorkoutLogResponse(BaseModel):
    id: str
    raw_text: str
    confirmed_data: Dict[str, Any]
    logged_at: datetime

    class Config:
        from_attributes = True

