"""Logging API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas.logs import (
    MealParseRequest,
    MealParseResponse,
    MealLogCreateRequest,
    MealLogResponse,
)
from app.services.nutritionist.logging.meal_logging_service import MealLoggingService

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


