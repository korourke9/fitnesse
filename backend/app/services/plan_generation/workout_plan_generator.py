"""Workout plan generation service using AWS Bedrock."""
import uuid
from datetime import date, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.plan import Plan, PlanType
from app.models.goal import GoalType
from app.services.plan_generation.base import BasePlanGenerator


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
    
    def _build_prompt(self, existing_meal_plan: Optional[Dict[str, Any]] = None) -> str:
        """Build prompt for workout plan generation."""
        profile_context = self._get_profile_context()
        goals_context = self._get_goals_context(self.RELEVANT_GOAL_TYPES)
        goal_implications = self._get_goal_implications(self.RELEVANT_GOAL_TYPES)
        
        # Also include all goals for full context
        all_goals_context = self._get_goals_context()
        
        # Include meal plan context if available
        meal_plan_context = ""
        if existing_meal_plan:
            meal_plan_context = f"""
Existing Meal Plan (coordinate workout recommendations with nutrition):
- Daily calories: {existing_meal_plan.get('daily_calories', 'N/A')}
- Protein intake: {existing_meal_plan.get('macros', {}).get('protein', 'N/A')}g/day
- Meals per day: {existing_meal_plan.get('meals_per_day', 'N/A')}

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
   - What type of workout each day
   - Brief description of focus for each day
   - Include rest days

5. **Sample Exercises** for each focus area:
   - Exercises appropriate for their level
   - Respect any physical limitations
   - Equipment considerations based on preferences

6. **Plan Notes**: Explain why this workout plan fits their specific goals

Return ONLY valid JSON with this structure:
{{
  "workouts_per_week": <number>,
  "workout_duration_minutes": <number>,
  "focus_areas": ["area1", "area2"],
  "guidelines": ["guideline 1", "guideline 2", ...],
  "weekly_schedule": [
    {{"day": 1, "type": "Workout Type", "description": "Focus details"}},
    {{"day": 2, "type": "Rest", "description": "Active recovery"}},
    ...
  ],
  "sample_exercises": {{
    "strength": ["exercise 1", "exercise 2"],
    "cardio": ["exercise 1", "exercise 2"],
    "flexibility": ["exercise 1", "exercise 2"]
  }},
  "notes": "Personalized explanation"
}}"""
    
    def _get_fallback_plan(self) -> Dict[str, Any]:
        """Get fallback workout plan if generation fails."""
        return {
            "workouts_per_week": 4,
            "workout_duration_minutes": 45,
            "focus_areas": ["strength", "cardio", "flexibility"],
            "guidelines": [
                "Always warm up for 5-10 minutes before workouts",
                "Rest at least one day between intense strength sessions",
                "Listen to your body - rest when needed",
                "Focus on form over weight or speed",
                "Stay hydrated during workouts",
                "Cool down and stretch after each session"
            ],
            "weekly_schedule": [
                {"day": 1, "type": "Upper Body Strength", "description": "Focus on chest, back, and shoulders"},
                {"day": 2, "type": "Cardio + Core", "description": "30 min cardio, 15 min core work"},
                {"day": 3, "type": "Rest", "description": "Active recovery - light walking or stretching"},
                {"day": 4, "type": "Lower Body Strength", "description": "Focus on legs and glutes"},
                {"day": 5, "type": "Cardio + Flexibility", "description": "30 min cardio, stretching"},
                {"day": 6, "type": "Full Body", "description": "Light full body workout"},
                {"day": 7, "type": "Rest", "description": "Complete rest day"}
            ],
            "sample_exercises": {
                "strength": ["Push-ups", "Squats", "Lunges", "Rows", "Planks"],
                "cardio": ["Walking", "Jogging", "Cycling", "Swimming"],
                "flexibility": ["Stretching", "Yoga poses", "Foam rolling"]
            },
            "notes": "A balanced workout plan to support your fitness goals. Adjust intensity based on how you feel."
        }
    
    def _get_or_create_plan(self, duration_days: int = 30) -> Plan:
        """Get existing active plan or create a new one."""
        existing_plan = self.db.query(Plan).filter(
            Plan.user_id == self.user_id,
            Plan.plan_type == PlanType.WORKOUT,
            Plan.is_active == True
        ).first()
        
        if existing_plan:
            return existing_plan
        
        start_date = date.today()
        end_date = start_date + timedelta(days=duration_days - 1)
        
        plan = Plan(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            plan_type=PlanType.WORKOUT,
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
        if meal_plan and isinstance(meal_plan.plan_data, dict):
            existing_meal_plan = meal_plan.plan_data
        
        prompt = self._build_prompt(existing_meal_plan)
        
        messages = [{
            "role": "user",
            "content": prompt
        }]
        
        try:
            response = await self.bedrock.invoke(
                messages=messages,
                system_prompt="You are an expert personal trainer. Respond with valid JSON only, no markdown or explanation.",
                max_tokens=2048,
                temperature=0.7
            )
            
            workout_plan_data = self._parse_json_response(response)
            
        except Exception as e:
            print(f"Error generating workout plan: {str(e)}")
            workout_plan_data = self._get_fallback_plan()
        
        # Update plan with workout plan data
        plan.plan_data = workout_plan_data
        
        self.db.commit()
        self.db.refresh(plan)
        
        return plan

