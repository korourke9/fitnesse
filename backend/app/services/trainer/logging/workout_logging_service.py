"""Workout logging/parsing service."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.dao import UserDAO, PlanDAO
from app.models.plan import PlanType
from app.models.log import Log, LogType
from app.schemas.plan_data import WorkoutPlanData
from app.services.bedrock import BedrockService
from app.services.trainer.logging.workout_logging_schema import WorkoutParseResult


class WorkoutLoggingService:
    """Parses and saves workout logs."""

    def __init__(self, db: Session, model_id: Optional[str] = None):
        self.db = db
        self.user_dao = UserDAO(db)
        self.plan_dao = PlanDAO(db)
        self.bedrock = BedrockService(model_id=model_id)

    def _require_active_workout_plan(self, user_id: str) -> None:
        plan = self.plan_dao.get_active_plan(user_id, PlanType.WORKOUT)
        if not plan:
            raise HTTPException(
                status_code=400,
                detail="No active workout plan. Generate a workout plan before logging workouts.",
            )
        try:
            WorkoutPlanData.from_stored(plan.plan_data)  # Validate plan_data is valid
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Workout plan data is invalid. Please regenerate your workout plan.",
            )

    def parse_workout(self, text: str) -> Dict[str, Any]:
        user = self.user_dao.get_or_create_temp_user()
        self._require_active_workout_plan(user.id)

        schema = WorkoutParseResult.model_json_schema(mode="serialization")
        system_prompt = (
            "You are a personal trainer assistant. Parse the user's workout description into structured data.\n\n"
            "EXERCISES: Extract every exercise mentioned. For each exercise provide:\n"
            "- name: exercise name (e.g. 'Bench Press', 'Running', 'Incline Walk')\n"
            "- sets: number of sets if given (e.g. 3 for '3x8')\n"
            "- reps: reps per set if given (e.g. '8' or '8-10')\n"
            "- weight: weight used if given (e.g. '135 lbs', 'bodyweight')\n"
            "- duration: for cardio (e.g. '30 min', '5 miles', '15 min')\n"
            "Examples: 'bench 3x8' -> name=Bench Press, sets=3, reps='8'; '15 min incline walk' -> name=Incline Walk, duration='15 min'.\n\n"
            "TOTAL: Estimate total_duration_minutes (sum of all exercise durations; for resistance assume ~3 min per set if not stated). "
            "Estimate estimated_calories_burned (rough: cardio ~8-12 cal/min, resistance ~5-8 cal/min depending on intensity).\n"
            "normalized_text: a clean one-line summary of the workout.\n"
            "confidence: 0.0-1.0. Use questions[] only if critical info is missing.\n"
            "Output valid JSON matching the schema exactly."
        )

        try:
            result = self.bedrock.invoke_structured(
                messages=[{"role": "user", "content": text}],
                output_schema=schema,
                system_prompt=system_prompt,
                max_tokens=1200,
                temperature=0.2,
            )
            # Validate
            parsed = WorkoutParseResult.model_validate(result)
            return parsed.model_dump()
        except Exception as e:
            # Fallback: minimal structured output
            return WorkoutParseResult(
                normalized_text=text.strip(),
                confidence=0.2,
                questions=["What exercises did you do? How many sets and reps?"],
                metadata={"error": str(e)},
            ).model_dump()

    def save_workout_log(
        self,
        raw_text: str,
        parsed_data: Optional[Dict[str, Any]],
        confirmed_data: Dict[str, Any],
        logged_at: Optional[datetime] = None,
    ) -> Log:
        user = self.user_dao.get_or_create_temp_user()
        self._require_active_workout_plan(user.id)

        if logged_at is None:
            logged_at = datetime.now(timezone.utc)

        log = Log(
            user_id=user.id,
            log_type=LogType.WORKOUT,
            raw_text=raw_text,
            parsed_data=parsed_data,
            confirmed_data=confirmed_data,
            logged_at=logged_at,
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
