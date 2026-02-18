"""Workout plan generation service using AWS Bedrock."""
import uuid
from datetime import date
from typing import Optional
from sqlalchemy.orm import Session

from app.models.plan import Plan, PlanType
from app.models.goal import GoalType
from app.schemas.plan_data import MealPlanData, WorkoutPlanData
from app.services.plan_generation.base import BasePlanGenerator

# Schema for Bedrock structured output: LLM must return JSON matching this shape
WORKOUT_PLAN_OUTPUT_SCHEMA = WorkoutPlanData.model_json_schema(mode="serialization")


class WorkoutPlanGenerator(BasePlanGenerator):
    """Service for generating personalized workout/exercise plans."""
    
    # Goal types relevant to workout planning
    RELEVANT_GOAL_TYPES = [
        GoalType.WEIGHT_LOSS,
        GoalType.WEIGHT_GAIN,
        GoalType.MUSCLE_GAIN,
        GoalType.ENDURANCE,
        GoalType.FLEXIBILITY,
        GoalType.BODY_FAT_PERCENTAGE,
        GoalType.LONGEVITY,
        GoalType.GENERAL_FITNESS,
    ]
    
    def _build_prompt(self, existing_meal_plan: Optional[MealPlanData] = None) -> str:
        """Build prompt for workout plan generation."""
        profile_context = self._get_profile_context()
        goals_context = self._get_goals_context(self.RELEVANT_GOAL_TYPES)
        goal_implications = self._get_goal_implications(self.RELEVANT_GOAL_TYPES)
        
        # Also include all goals for full context
        all_goals_context = self._get_goals_context()
        
        # Include meal plan context if available
        meal_plan_context = ""
        if existing_meal_plan:
            calories = existing_meal_plan.daily_calories or 'N/A'
            protein = existing_meal_plan.macros.get('protein', 'N/A') if existing_meal_plan.macros else 'N/A'
            meals_per_day = existing_meal_plan.meals_per_day or 'N/A'
            meal_plan_context = f"""
Existing Meal Plan (coordinate workout recommendations with nutrition):
- Daily calories: {calories}
- Protein intake: {protein}g/day
- Meals per day: {meals_per_day}

Consider: Is protein sufficient for muscle building? Is there a caloric deficit/surplus that affects workout intensity recommendations?
"""
        
        return f"""You are an expert personal trainer creating a personalized workout plan.
Use the following information about the user to create a tailored exercise program.

{profile_context}

{goals_context}

{goal_implications}

{f"All User Goals (for context):{chr(10)}{all_goals_context}" if all_goals_context != goals_context else ""}

{meal_plan_context}

Create a detailed, personalized workout plan that includes:

1. **Weekly Structure**:
   - Number of workouts per week (appropriate for their activity level and goals)
   - Workout duration per session
   - Rest day recommendations

2. **Focus Areas**: Based on their goals
   - Strength training focus areas
   - Cardio recommendations
   - Flexibility/mobility work
   - Any areas to avoid or modify (based on conditions/preferences)

3. **Workout Guidelines** (5-7 specific, actionable guidelines):
   - Warm-up and cool-down recommendations
   - Intensity and progression guidance
   - Form and safety tips
   - Recovery recommendations

4. **Weekly Schedule**: Day-by-day breakdown
   - What type of workout each day (all 7 days: day 1 = Monday, day 7 = Sunday)
   - Brief description of focus for each day
   - Specific exercises for each workout day (optional but recommended)
   - Include rest days

5. **Sample Exercises** for each focus area:
   - Exercises appropriate for their level
   - Respect any physical limitations
   - Equipment considerations based on preferences

6. **Plan Notes**: Explain why this workout plan fits their specific goals"""
    
    def _get_or_create_plan(self, duration_days: int = 30) -> Plan:
        """Get existing active plan or create a new one."""
        existing_plan = self.db.query(Plan).filter(
            Plan.user_id == self.user_id,
            Plan.plan_type == PlanType.WORKOUT,
            Plan.is_active == True
        ).first()
        
        if existing_plan:
            # Validate existing plan_data is valid
            try:
                WorkoutPlanData.from_stored(existing_plan.plan_data)
            except Exception:
                # If plan_data is invalid, treat as if no plan exists (will regenerate)
                pass
            else:
                return existing_plan
        
        start_date = date.today()
        
        plan = Plan(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            plan_type=PlanType.WORKOUT,
            name=f"{start_date.strftime('%B %Y')} Plan",
            start_date=start_date,
            end_date=None,  # Plans are ongoing until replaced
            duration_days=None,  # No longer used
            plan_data={},
            is_active=True,
            is_completed=False
        )
        
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        
        return plan
    
    async def generate(self, duration_days: int = 30) -> Plan:
        """
        Generate a personalized workout plan.
        
        If a meal plan exists, it will be used for context to ensure
        the workout plan is coordinated with nutrition.
        
        Args:
            duration_days: Duration of the plan in days (default: 30)
        
        Returns:
            Plan object with workout plan data in plan_data["exercise"]
        """
        plan = self._get_or_create_plan(duration_days)
        
        # Get existing meal plan (separate plan type) for context if available
        existing_meal_plan = None
        meal_plan = self.db.query(Plan).filter(
            Plan.user_id == self.user_id,
            Plan.plan_type == PlanType.MEAL,
            Plan.is_active == True
        ).first()
        if meal_plan:
            try:
                existing_meal_plan = MealPlanData.from_stored(meal_plan.plan_data)
            except Exception:
                # If meal plan data is invalid, skip it (don't fail workout generation)
                pass
        
        prompt = self._build_prompt(existing_meal_plan)
        messages = [{"role": "user", "content": prompt}]
        system_prompt = (
            "You are an expert personal trainer. Create a personalized workout plan. "
            "Your response must be valid JSON that matches the required schema exactly."
        )
        
        result = self.bedrock.invoke_structured(
            messages=messages,
            output_schema=WORKOUT_PLAN_OUTPUT_SCHEMA,
            system_prompt=system_prompt,
            max_tokens=4096,
            temperature=0.5,
        )
        canonical = WorkoutPlanData.model_validate(result)
        plan.plan_data = canonical.model_dump(mode="json")
        
        self.db.commit()
        self.db.refresh(plan)
        
        return plan

