"""Deterministic plan generation and view endpoints (non-chat)."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dao import PlanDAO, UserDAO
from app.api.schemas.plans import (
    PlanGenerateRequest,
    PlanGenerateSummary,
    PlanViewResponse,
)
from app.models.plan import PlanType
from app.schemas.plan_data import MealPlanData, WorkoutPlanData
from app.services.nutritionist import NutritionService
from app.services.trainer import TrainingService

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.post("/meal", response_model=PlanGenerateSummary)
async def create_meal_plan(
    request: PlanGenerateRequest,
    db: Session = Depends(get_db),
):
    service = NutritionService(db)
    plan = await service.generate_meal_plan(duration_days=request.duration_days)

    # plan.plan_data is already canonical (from MealPlanGenerator)
    meal_data = MealPlanData.from_stored(plan.plan_data)
    return PlanGenerateSummary(
        plan_id=plan.id,
        start_date=plan.start_date,
        end_date=plan.end_date,  # May be None for ongoing plans
        duration_days=plan.duration_days,  # May be None
        data=meal_data.model_dump(mode="json", exclude_none=False),
    )


@router.post("/workout", response_model=PlanGenerateSummary)
async def create_workout_plan(
    request: PlanGenerateRequest,
    db: Session = Depends(get_db),
):
    service = TrainingService(db)
    plan = await service.generate_workout_plan(duration_days=request.duration_days)

    # plan.plan_data is already canonical (from WorkoutPlanGenerator)
    workout_data = WorkoutPlanData.from_stored(plan.plan_data)
    return PlanGenerateSummary(
        plan_id=plan.id,
        start_date=plan.start_date,
        end_date=plan.end_date,  # May be None for ongoing plans
        duration_days=plan.duration_days,  # May be None
        data=workout_data.model_dump(mode="json", exclude_none=False),
    )


@router.get("/{plan_id}/view", response_model=PlanViewResponse)
async def get_plan_view(
    plan_id: str,
    query_date: Optional[date] = Query(None, alias="date", description="Date for the view (default: today)"),
    db: Session = Depends(get_db),
) -> PlanViewResponse:
    """Get today's view for a plan (meals or workout) for the given date."""
    view_date = query_date if query_date is not None else date.today()
    user = UserDAO(db).get_or_create_temp_user()
    plan = PlanDAO(db).get_by_id(plan_id, user.id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan.plan_type == PlanType.MEAL:
        service = NutritionService(db)
        payload = service.get_today_view_for_plan(plan, view_date)
    elif plan.plan_type == PlanType.WORKOUT:
        service = TrainingService(db)
        payload = service.get_today_view_for_plan(plan, view_date)
    else:
        raise HTTPException(status_code=400, detail="Unsupported plan type")

    return PlanViewResponse(**payload)


