"""Meal plan generation service using AWS Bedrock."""
import uuid
from datetime import date, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.plan import Plan, PlanType
from app.models.goal import GoalType
from app.services.plan_generation.base import BasePlanGenerator


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

5. **Sample Meals** (2-3 options for each meal type):
   - Respect dietary preferences
   - Consider cooking time constraints
   - Budget-appropriate suggestions

6. **Plan Notes**: Explain why this plan fits their specific goals and situation

Return ONLY valid JSON with this structure:
{{
  "daily_calories": <number>,
  "macros": {{
    "protein": <grams>,
    "carbs": <grams>,
    "fat": <grams>
  }},
  "meals_per_day": <number>,
  "guidelines": ["guideline 1", "guideline 2", ...],
  "sample_meals": {{
    "breakfast": ["option 1", "option 2"],
    "lunch": ["option 1", "option 2"],
    "dinner": ["option 1", "option 2"],
    "snacks": ["option 1", "option 2"]
  }},
  "notes": "Personalized explanation"
}}"""
    
    def _get_fallback_plan(self) -> Dict[str, Any]:
        """Get fallback meal plan if generation fails."""
        return {
            "daily_calories": 2000,
            "macros": {"protein": 150, "carbs": 200, "fat": 65},
            "meals_per_day": 3,
            "guidelines": [
                "Eat balanced meals with protein, carbs, and healthy fats",
                "Stay hydrated - aim for 8 glasses of water daily",
                "Include vegetables with every meal",
                "Plan meals ahead to stay on track",
                "Listen to hunger cues and eat mindfully"
            ],
            "sample_meals": {
                "breakfast": ["Oatmeal with berries and nuts", "Eggs with whole grain toast"],
                "lunch": ["Grilled chicken salad", "Quinoa bowl with vegetables"],
                "dinner": ["Baked salmon with roasted vegetables", "Lean protein with brown rice"],
                "snacks": ["Greek yogurt", "Apple with almond butter"]
            },
            "notes": "A balanced nutrition plan to support your health goals. Adjust portions based on your hunger and energy levels."
        }
    
    def _get_or_create_plan(self, duration_days: int = 30) -> Plan:
        """Get existing active plan or create a new one."""
        existing_plan = self.db.query(Plan).filter(
            Plan.user_id == self.user_id,
            Plan.plan_type == PlanType.MEAL,
            Plan.is_active == True
        ).first()
        
        if existing_plan:
            return existing_plan
        
        start_date = date.today()
        end_date = start_date + timedelta(days=duration_days - 1)
        
        plan = Plan(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            plan_type=PlanType.MEAL,
            name=f"{start_date.strftime('%B %Y')} Plan",
            start_date=start_date,
            end_date=end_date,
            duration_days=duration_days,
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
        Generate a personalized meal plan.
        
        Args:
            duration_days: Duration of the plan in days (default: 30)
        
        Returns:
            Plan object with meal plan data in plan_data["diet"]
        """
        plan = self._get_or_create_plan(duration_days)
        
        prompt = self._build_prompt()
        
        messages = [{
            "role": "user",
            "content": prompt
        }]
        
        try:
            response = await self.bedrock.invoke(
                messages=messages,
                system_prompt="You are an expert nutritionist. Respond with valid JSON only, no markdown or explanation.",
                max_tokens=2048,
                temperature=0.7
            )
            
            meal_plan_data = self._parse_json_response(response)
            
        except Exception as e:
            print(f"Error generating meal plan: {str(e)}")
            meal_plan_data = self._get_fallback_plan()
        
        # Update plan with meal plan data
        plan.plan_data = meal_plan_data
        
        self.db.commit()
        self.db.refresh(plan)
        
        return plan

