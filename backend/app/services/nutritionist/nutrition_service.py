"""Nutrition domain service (deterministic APIs)."""
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.dao import UserDAO, UserProfileDAO, GoalDAO, PlanDAO
from app.models.plan import Plan
from app.services.plan_generation import MealPlanGenerator
from app.models.plan import PlanType


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
        if existing and isinstance(existing.plan_data, dict) and existing.plan_data:
            raise HTTPException(
                status_code=409,
                detail=f"Active meal plan already exists (plan_id={existing.id}). Use plan update/feedback instead of creating a new plan.",
            )

        generator = MealPlanGenerator(db=self.db, user_id=user.id)
        return await generator.generate(duration_days=duration_days)


