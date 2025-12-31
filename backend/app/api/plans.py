"""Plan API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models.user import User
from app.models.plan import Plan
from app.services.plan_generation import MealPlanGenerator, WorkoutPlanGenerator

router = APIRouter(prefix="/api/plans", tags=["plans"])


class PlanResponse(BaseModel):
    """Schema for plan response."""
    id: str
    name: Optional[str]
    start_date: str
    end_date: str
    duration_days: int
    plan_data: dict
    is_active: bool
    is_completed: bool
    has_meal_plan: bool
    has_workout_plan: bool
    
    class Config:
        from_attributes = True


@router.get("/active", response_model=Optional[PlanResponse])
async def get_active_plan(db: Session = Depends(get_db)):
    """Get the active plan for the current user."""
    # TODO: Get from authentication
    temp_user_id = "temp-user-123"
    
    plan = db.query(Plan).filter(
        Plan.user_id == temp_user_id,
        Plan.is_active == True
    ).first()
    
    if not plan:
        return None
    
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        start_date=plan.start_date.isoformat(),
        end_date=plan.end_date.isoformat(),
        duration_days=plan.duration_days,
        plan_data=plan.plan_data or {},
        is_active=plan.is_active,
        is_completed=plan.is_completed,
        has_meal_plan=bool(plan.plan_data and plan.plan_data.get("diet")),
        has_workout_plan=bool(plan.plan_data and plan.plan_data.get("exercise"))
    )


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: str, db: Session = Depends(get_db)):
    """Get a specific plan by ID."""
    # TODO: Get from authentication
    temp_user_id = "temp-user-123"
    
    plan = db.query(Plan).filter(
        Plan.id == plan_id,
        Plan.user_id == temp_user_id
    ).first()
    
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        start_date=plan.start_date.isoformat(),
        end_date=plan.end_date.isoformat(),
        duration_days=plan.duration_days,
        plan_data=plan.plan_data or {},
        is_active=plan.is_active,
        is_completed=plan.is_completed,
        has_meal_plan=bool(plan.plan_data and plan.plan_data.get("diet")),
        has_workout_plan=bool(plan.plan_data and plan.plan_data.get("exercise"))
    )


@router.post("/generate-meal")
async def generate_meal_plan(db: Session = Depends(get_db)):
    """Generate meal plan for the user."""
    # TODO: Get from authentication
    temp_user_id = "temp-user-123"
    
    generator = MealPlanGenerator(db=db, user_id=temp_user_id)
    plan = await generator.generate()
    
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        start_date=plan.start_date.isoformat(),
        end_date=plan.end_date.isoformat(),
        duration_days=plan.duration_days,
        plan_data=plan.plan_data or {},
        is_active=plan.is_active,
        is_completed=plan.is_completed,
        has_meal_plan=bool(plan.plan_data and plan.plan_data.get("diet")),
        has_workout_plan=bool(plan.plan_data and plan.plan_data.get("exercise"))
    )


@router.post("/generate-workout")
async def generate_workout_plan(db: Session = Depends(get_db)):
    """Generate workout plan for the user."""
    # TODO: Get from authentication
    temp_user_id = "temp-user-123"
    
    generator = WorkoutPlanGenerator(db=db, user_id=temp_user_id)
    plan = await generator.generate()
    
    return PlanResponse(
        id=plan.id,
        name=plan.name,
        start_date=plan.start_date.isoformat(),
        end_date=plan.end_date.isoformat(),
        duration_days=plan.duration_days,
        plan_data=plan.plan_data or {},
        is_active=plan.is_active,
        is_completed=plan.is_completed,
        has_meal_plan=bool(plan.plan_data and plan.plan_data.get("diet")),
        has_workout_plan=bool(plan.plan_data and plan.plan_data.get("exercise"))
    )

