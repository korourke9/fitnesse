"""Nutrition domain service (deterministic APIs)."""
from datetime import date
from typing import Any, Dict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.dao import UserDAO, UserProfileDAO, GoalDAO, PlanDAO
from app.models.plan import Plan, PlanType
from app.services.nutritionist.planning import MealPlanData, MealPlanGenerator


class NutritionService:
    """Nutrition service for plan generation and nutrition workflows."""

    def __init__(self, db: Session):
        self.db = db
        self.user_dao = UserDAO(db)
        self.profile_dao = UserProfileDAO(db)
        self.goal_dao = GoalDAO(db)
        self.plan_dao = PlanDAO(db)

    def _require_onboarding_complete(self, user_id: str) -> None:
        profile = self.profile_dao.get_by_user_id(user_id)
        goals = self.goal_dao.get_active_goals(user_id)
        if not profile or not goals:
            raise HTTPException(
                status_code=400,
                detail="Onboarding incomplete. Please complete onboarding before generating a plan.",
            )

    async def generate_meal_plan(self, duration_days: int = 30) -> Plan:
        user = self.user_dao.get_or_create_temp_user()
        self._require_onboarding_complete(user.id)

        existing = self.plan_dao.get_active_plan(user.id, PlanType.MEAL)
        if existing:
            try:
                MealPlanData.from_stored(existing.plan_data)  # Validate plan exists and is valid
                raise HTTPException(
                    status_code=409,
                    detail=f"Active meal plan already exists (plan_id={existing.id}). Use plan update/feedback instead of creating a new plan.",
                )
            except (ValueError, TypeError, KeyError):
                # Plan exists but data is invalid - allow regeneration
                pass

        generator = MealPlanGenerator(db=self.db, user_id=user.id)
        return await generator.generate(duration_days=duration_days)

    def get_today_view_for_plan(self, plan: Plan, view_date: date, include_detail: bool = True) -> Dict[str, Any]:
        """Build today's meal view from the plan's canonical data (no fallback logic)."""
        model = MealPlanData.from_stored(plan.plan_data)
        day_num = view_date.weekday() + 1  # 1=Monday .. 7=Sunday
        day_meals = next((d for d in model.weekly_schedule if d.day == day_num), None)
        meals = []
        if day_meals:
            meals = [
                {
                    "meal_type": m.meal_type,
                    "name": m.name,
                    "nutrition": m.nutrition,
                    "ingredients": m.ingredients if include_detail else None,
                    "instructions": m.instructions if include_detail else None,
                }
                for m in day_meals.meals  # m is MealRecipe
            ]
        return {
            "date": view_date.isoformat(),
            "plan_type": PlanType.MEAL.value,
            "targets": {
                "daily_calories": model.daily_calories,
                "macros": model.macros,
            },
            "meals": meals,
        }

