"""Service for returning application state to the frontend."""
from typing import Optional
from sqlalchemy.orm import Session

from app.dao import UserDAO, PlanDAO, GoalDAO, UserProfileDAO
from app.api.schemas.state import AppStateResponse, SectionState, PlanSummary
from app.models.plan import PlanType
from app.models.log import Log, LogType
from app.schemas.plan_data import MealPlanData, WorkoutPlanData


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

        # Load plan models (handles legacy data via from_stored)
        # Gracefully handle invalid plan_data by treating as no plan
        meal_model = None
        if active_meal_plan:
            try:
                meal_model = MealPlanData.from_stored(active_meal_plan.plan_data)
            except Exception:
                # Invalid plan_data - treat as if no plan exists
                pass
        
        workout_model = None
        if active_workout_plan:
            try:
                workout_model = WorkoutPlanData.from_stored(active_workout_plan.plan_data)
            except Exception:
                # Invalid plan_data - treat as if no plan exists
                pass

        nutrition_summary = self._build_plan_summary(active_meal_plan, meal_model)
        training_summary = self._build_plan_summary_workout(active_workout_plan, workout_model)

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
                has_plan=meal_model is not None,
                plan_id=active_meal_plan.id if active_meal_plan else None,
                summary=nutrition_summary if meal_model else None,
            ),
            training=SectionState(
                has_plan=workout_model is not None,
                plan_id=active_workout_plan.id if active_workout_plan else None,
                summary=training_summary if workout_model else None,
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
        plan_model: Optional[MealPlanData],
    ) -> Optional[PlanSummary]:
        """Build meal plan summary from plan model. Returns None if no model provided."""
        if not plan_model:
            return None

        summary = PlanSummary()
        if plan:
            summary.start_date = plan.start_date
            summary.end_date = plan.end_date  # May be None for ongoing plans
            summary.duration_days = plan.duration_days  # May be None

        summary.daily_calories = plan_model.daily_calories
        summary.macros = plan_model.macros
        summary.notes = plan_model.notes

        return summary

    def _build_plan_summary_workout(
        self,
        plan,
        plan_model: Optional[WorkoutPlanData],
    ) -> Optional[PlanSummary]:
        """Build workout plan summary from plan model. Returns None if no model provided."""
        if not plan_model:
            return None

        summary = PlanSummary()
        if plan:
            summary.start_date = plan.start_date
            summary.end_date = plan.end_date  # May be None for ongoing plans
            summary.duration_days = plan.duration_days  # May be None

        summary.workouts_per_week = plan_model.workouts_per_week
        summary.notes = plan_model.notes

        return summary


