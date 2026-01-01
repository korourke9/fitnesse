"""State API endpoint."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.schemas.state import AppStateResponse
from app.services.state import StateService

router = APIRouter(prefix="/api", tags=["state"])


@router.get("/state", response_model=AppStateResponse)
async def get_state(db: Session = Depends(get_db)) -> AppStateResponse:
    """Get application bootstrap state for the current user."""
    service = StateService(db)
    return service.get_state()


