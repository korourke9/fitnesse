"""Deterministic plan generation endpoints (non-chat)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas.plans import PlanGenerateRequest, PlanGenerateSummary
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

    diet = plan.plan_data if isinstance(plan.plan_data, dict) else None
    return PlanGenerateSummary(
        plan_id=plan.id,
        start_date=plan.start_date,
        end_date=plan.end_date,
        duration_days=plan.duration_days,
        data=diet if isinstance(diet, dict) else {},
    )


@router.post("/workout", response_model=PlanGenerateSummary)
async def create_workout_plan(
    request: PlanGenerateRequest,
    db: Session = Depends(get_db),
):
    service = TrainingService(db)
    plan = await service.generate_workout_plan(duration_days=request.duration_days)

    exercise = plan.plan_data if isinstance(plan.plan_data, dict) else None
    return PlanGenerateSummary(
        plan_id=plan.id,
        start_date=plan.start_date,
        end_date=plan.end_date,
        duration_days=plan.duration_days,
        data=exercise if isinstance(exercise, dict) else {},
    )


