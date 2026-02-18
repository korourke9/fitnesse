"""Service for returning application state to the frontend."""
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session

from app.dao import UserDAO, PlanDAO, GoalDAO, UserProfileDAO
from app.api.schemas.state import AppStateResponse, SectionState, PlanSummary
from app.models.plan import PlanType
from app.models.log import Log, LogType


class StateService:
    """Builds a bootstrap state payload for the frontend."""

    def __init__(self, db: Session):
        self.db = db
        self.user_dao = UserDAO(db)
        self.plan_dao = PlanDAO(db)
        self.goal_dao = GoalDAO(db)
        self.profile_dao = UserProfileDAO(db)

    def get_state(self) -> AppStateResponse:
        user = self.user_dao.get_or_create_temp_user()

        profile = self.profile_dao.get_by_user_id(user.id)
        goals = self.goal_dao.get_active_goals(user.id)
        active_meal_plan = self.plan_dao.get_active_plan(user.id, PlanType.MEAL)
        active_workout_plan = self.plan_dao.get_active_plan(user.id, PlanType.WORKOUT)

        onboarding_complete = bool(goals) and bool(profile)

        meal_data: Dict[str, Any] = (
            active_meal_plan.plan_data if (active_meal_plan and isinstance(active_meal_plan.plan_data, dict)) else {}
        )
        workout_data: Dict[str, Any] = (
            active_workout_plan.plan_data if (active_workout_plan and isinstance(active_workout_plan.plan_data, dict)) else {}
        )

        nutrition_summary = self._build_plan_summary(active_meal_plan, plan_data=meal_data, plan_type=PlanType.MEAL)
        training_summary = self._build_plan_summary(active_workout_plan, plan_data=workout_data, plan_type=PlanType.WORKOUT)

        recent_checkins = (
            self.db.query(Log)
            .filter(Log.user_id == user.id)
            .filter(Log.log_type == LogType.GOAL_CHECKIN)
            .order_by(Log.logged_at.desc())
            .limit(5)
            .all()
        )

        return AppStateResponse(
            user_id=user.id,
            onboarding_complete=onboarding_complete,
            nutrition=SectionState(
                has_plan=bool(active_meal_plan and meal_data),
                plan_id=active_meal_plan.id if (active_meal_plan and meal_data) else None,
                summary=nutrition_summary if (active_meal_plan and meal_data) else None,
            ),
            training=SectionState(
                has_plan=bool(active_workout_plan and workout_data),
                plan_id=active_workout_plan.id if (active_workout_plan and workout_data) else None,
                summary=training_summary if (active_workout_plan and workout_data) else None,
            ),
            goals=[
                {
                    "id": g.id,
                    "goal_type": g.goal_type.value,
                    "description": g.description,
                    "target": g.target,
                    "target_value": g.target_value,
                    "target_date": g.target_date.isoformat() if g.target_date else None,
                }
                for g in goals
            ],
            recent_goal_checkins=[
                {
                    "id": c.id,
                    "text": c.raw_text,
                    "logged_at": c.logged_at.isoformat(),
                }
                for c in recent_checkins
            ],
        )

    def _build_plan_summary(
        self,
        plan,
        plan_data: Dict[str, Any],
        plan_type: PlanType,
    ) -> PlanSummary:
        summary = PlanSummary()
        if plan:
            summary.start_date = plan.start_date
            summary.end_date = plan.end_date
            summary.duration_days = plan.duration_days

        if plan_type == PlanType.MEAL:
            summary.daily_calories = plan_data.get("daily_calories")
            summary.macros = plan_data.get("macros")
        elif plan_type == PlanType.WORKOUT:
            summary.workouts_per_week = plan_data.get("workouts_per_week")

        notes = plan_data.get("notes")
        if isinstance(notes, str):
            summary.notes = notes

        return summary


