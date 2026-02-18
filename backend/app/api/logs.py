"""Logging API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas.logs import (
    MealParseRequest,
    MealParseResponse,
    MealLogCreateRequest,
    MealLogResponse,
    GoalCheckInCreateRequest,
    GoalCheckInResponse,
    WorkoutParseRequest,
    WorkoutParseResponse,
    WorkoutLogCreateRequest,
    WorkoutLogResponse,
)
from app.services.nutritionist.logging.meal_logging_service import MealLoggingService
from app.services.trainer.logging.workout_logging_service import WorkoutLoggingService
from datetime import datetime, timezone
from app.dao import UserDAO
from app.models.log import Log, LogType

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.post("/meals/parse", response_model=MealParseResponse)
async def parse_meal(request: MealParseRequest, db: Session = Depends(get_db)) -> MealParseResponse:
    service = MealLoggingService(db)
    parsed = service.parse_meal(request.text)
    return MealParseResponse(parsed=parsed)


@router.post("/meals", response_model=MealLogResponse)
async def create_meal_log(request: MealLogCreateRequest, db: Session = Depends(get_db)) -> MealLogResponse:
    service = MealLoggingService(db)
    log = service.save_meal_log(
        raw_text=request.raw_text,
        parsed_data=request.parsed_data,
        confirmed_data=request.confirmed_data,
        logged_at=request.logged_at,
    )
    return MealLogResponse.model_validate(log)


@router.post("/goals", response_model=GoalCheckInResponse)
async def create_goal_checkin(
    request: GoalCheckInCreateRequest,
    db: Session = Depends(get_db),
) -> GoalCheckInResponse:
    user = UserDAO(db).get_or_create_temp_user()
    logged_at = request.logged_at or datetime.now(timezone.utc)

    log = Log(
        user_id=user.id,
        log_type=LogType.GOAL_CHECKIN,
        raw_text=request.text,
        details=None,
        logged_at=logged_at,
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return GoalCheckInResponse(id=log.id, text=log.raw_text, logged_at=log.logged_at)


@router.post("/workouts/parse", response_model=WorkoutParseResponse)
async def parse_workout(request: WorkoutParseRequest, db: Session = Depends(get_db)) -> WorkoutParseResponse:
    service = WorkoutLoggingService(db)
    parsed = service.parse_workout(request.text)
    return WorkoutParseResponse(parsed=parsed)


@router.post("/workouts", response_model=WorkoutLogResponse)
async def create_workout_log(request: WorkoutLogCreateRequest, db: Session = Depends(get_db)) -> WorkoutLogResponse:
    service = WorkoutLoggingService(db)
    log = service.save_workout_log(
        raw_text=request.raw_text,
        parsed_data=request.parsed_data,
        confirmed_data=request.confirmed_data,
        logged_at=request.logged_at,
    )
    return WorkoutLogResponse.model_validate(log)

