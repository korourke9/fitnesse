"""Meal logging/parsing service."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.dao import UserDAO, PlanDAO
from app.models.plan import PlanType
from app.models.meal_log import MealLog
from app.services.bedrock import BedrockService
from app.services.nutritionist.logging.meal_logging_schema import MealParseResult


class MealLoggingService:
    """Parses and saves meal logs."""

    def __init__(self, db: Session, model_id: Optional[str] = None):
        self.db = db
        self.user_dao = UserDAO(db)
        self.plan_dao = PlanDAO(db)
        self.bedrock = BedrockService(model_id=model_id)

    def _require_active_meal_plan(self, user_id: str) -> None:
        plan = self.plan_dao.get_active_plan(user_id, PlanType.MEAL)
        if not plan or not isinstance(plan.plan_data, dict) or not plan.plan_data:
            raise HTTPException(
                status_code=400,
                detail="No active meal plan. Generate a meal plan before logging meals.",
            )

    def parse_meal(self, text: str) -> Dict[str, Any]:
        user = self.user_dao.get_or_create_temp_user()
        self._require_active_meal_plan(user.id)

        schema = MealParseResult.model_json_schema(mode="serialization")
        system_prompt = (
            "You are a nutritionist assistant. Convert the user's meal description into a structured estimate.\n"
            "- Keep questions minimal and only ask if needed to estimate.\n"
            "- Confidence should reflect uncertainty.\n"
            "- If you cannot estimate macros, leave them null and ask a question.\n"
            "- Output must match the schema exactly."
        )

        try:
            result = self.bedrock.invoke_structured(
                messages=[{"role": "user", "content": text}],
                output_schema=schema,
                system_prompt=system_prompt,
                max_tokens=800,
                temperature=0.2,
            )
            # Validate
            parsed = MealParseResult.model_validate(result)
            return parsed.model_dump()
        except Exception as e:
            # Fallback: minimal structured output
            return MealParseResult(
                normalized_text=text.strip(),
                confidence=0.2,
                questions=["Roughly how big was the portion? (small/medium/large)"],
                metadata={"error": str(e)},
            ).model_dump()

    def save_meal_log(
        self,
        raw_text: str,
        parsed_data: Optional[Dict[str, Any]],
        confirmed_data: Dict[str, Any],
        logged_at: Optional[datetime] = None,
    ) -> MealLog:
        user = self.user_dao.get_or_create_temp_user()
        self._require_active_meal_plan(user.id)

        if logged_at is None:
            logged_at = datetime.now(timezone.utc)

        log = MealLog(
            user_id=user.id,
            raw_text=raw_text,
            parsed_data=parsed_data,
            confirmed_data=confirmed_data,
            logged_at=logged_at,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log


