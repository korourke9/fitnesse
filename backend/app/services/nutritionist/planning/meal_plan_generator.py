"""Meal plan generation service using AWS Bedrock."""
import uuid
from datetime import date
from sqlalchemy.orm import Session

from app.models.plan import Plan, PlanType
from app.models.goal import GoalType
from app.services.nutritionist.planning.meal_plan_schema import MealPlanData
from app.services.plan_generation.base import BasePlanGenerator

# Schema for Bedrock structured output: LLM must return JSON matching this shape
MEAL_PLAN_OUTPUT_SCHEMA = MealPlanData.model_json_schema(mode="serialization")


class MealPlanGenerator(BasePlanGenerator):
    """Service for generating personalized meal/nutrition plans."""
    
    # Goal types relevant to meal planning
    RELEVANT_GOAL_TYPES = [
        GoalType.WEIGHT_LOSS,
        GoalType.WEIGHT_GAIN,
        GoalType.MUSCLE_GAIN,
        GoalType.NUTRITION,
        GoalType.BODY_FAT_PERCENTAGE,
        GoalType.LONGEVITY,
        GoalType.GENERAL_FITNESS,
    ]
    
    def _build_prompt(self) -> str:
        """Build prompt for meal plan generation."""
        profile_context = self._get_profile_context()
        goals_context = self._get_goals_context(self.RELEVANT_GOAL_TYPES)
        goal_implications = self._get_goal_implications(self.RELEVANT_GOAL_TYPES)
        
        # Also include all goals for full context
        all_goals_context = self._get_goals_context()
        
        return f"""You are an expert nutritionist creating a personalized meal plan. 
Use the following information about the user to create a tailored nutrition plan.

{profile_context}

{goals_context}

{goal_implications}

{f"All User Goals (for context):{chr(10)}{all_goals_context}" if all_goals_context != goals_context else ""}

Create a detailed, personalized nutrition plan that includes:

1. **Daily Calorie Target**: Calculate based on:
   - User's biometrics (height, weight, age, sex)
   - Activity level
   - Goals (deficit for weight loss, surplus for muscle gain, maintenance otherwise)

2. **Macro Breakdown**: Protein, carbs, fats in grams per day
   - Adjust based on goals (higher protein for muscle gain, balanced for general health)

3. **Meal Structure**: Number of meals per day based on preferences and lifestyle

4. **Nutrition Guidelines** (5-7 specific, actionable guidelines):
   - Tailored to dietary preferences and restrictions
   - Practical given cooking time and budget constraints
   - Aligned with their goals

5. **Weekly Schedule**: Day-by-day meal plan for the week
   - Provide meals for all 7 days (day 1 = Monday, day 7 = Sunday)
   - Each day should include breakfast, lunch, dinner, and optionally snacks
   - Vary meals across the week for variety and nutrition balance
   - Respect dietary preferences and cooking constraints
   - For each meal, include:
     * Name of the meal
     * Ingredients list (specific quantities when helpful)
     * Brief cooking instructions (2-4 steps, keep it simple)
     * Optional nutrition info (calories, protein, carbs, fat) if known

6. **Plan Notes**: Explain why this plan fits their specific goals and situation"""
    
    def _get_or_create_plan(self, duration_days: int = 30) -> Plan:
        """Get existing active plan or create a new one."""
        existing_plan = self.db.query(Plan).filter(
            Plan.user_id == self.user_id,
            Plan.plan_type == PlanType.MEAL,
            Plan.is_active == True
        ).first()
        
        if existing_plan:
            # Validate existing plan_data is valid
            try:
                MealPlanData.from_stored(existing_plan.plan_data)
            except Exception:
                # If plan_data is invalid, treat as if no plan exists (will regenerate)
                pass
            else:
                return existing_plan
        
        start_date = date.today()
        
        plan = Plan(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            plan_type=PlanType.MEAL,
            name=f"{start_date.strftime('%B %Y')} Plan",
            start_date=start_date,
            end_date=None,  # Plans are ongoing until replaced
            duration_days=None,  # No longer used
            plan_data={},
            is_active=True,
            is_completed=False
        )
        self.db.add(plan)
        # Do not commit here: commit only after plan_data is set in generate()
        return plan
    
    async def generate(self, duration_days: int = 30) -> Plan:
        """
        Generate a personalized meal plan.

        The plan row is only committed after plan_data is successfully
        generated and validated; on any exception the transaction is
        rolled back so no empty plan is left in the DB.
        """
        try:
            plan = self._get_or_create_plan(duration_days)

            prompt = self._build_prompt()
            messages = [{"role": "user", "content": prompt}]
            system_prompt = (
                "You are an expert nutritionist. Create a personalized meal plan. "
                "Your response must be valid JSON that matches the required schema exactly."
            )

            result = self.bedrock.invoke_structured(
                messages=messages,
                output_schema=MEAL_PLAN_OUTPUT_SCHEMA,
                system_prompt=system_prompt,
                max_tokens=4096,
                temperature=0.5,
            )
            canonical = MealPlanData.model_validate(result)
            plan.plan_data = canonical.model_dump(mode="json")

            self.db.commit()
            self.db.refresh(plan)
            return plan
        except Exception:
            self.db.rollback()
            raise
