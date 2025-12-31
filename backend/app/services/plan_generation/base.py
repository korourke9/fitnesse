"""Base plan generator with shared utilities."""
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.user_profile import UserProfile
from app.models.goal import Goal, GoalType
from app.services.bedrock import BedrockService


class BasePlanGenerator:
    """Base class for plan generators with shared context-building utilities."""
    
    def __init__(self, db: Session, user_id: str, model_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.bedrock = BedrockService(model_id=model_id)
        
        # Load user context
        self.profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == self.user_id
        ).first()
        self.goals = self.db.query(Goal).filter(
            Goal.user_id == self.user_id,
            Goal.is_active == True
        ).all()
    
    def _get_profile_context(self) -> str:
        """Build profile context string."""
        if not self.profile:
            return "No profile information available."
        
        context_parts = ["User Profile:"]
        
        if self.profile.height_cm:
            context_parts.append(f"- Height: {self.profile.height_cm} cm")
        if self.profile.weight_kg:
            context_parts.append(f"- Weight: {self.profile.weight_kg} kg")
        if self.profile.age:
            context_parts.append(f"- Age: {self.profile.age}")
        if self.profile.sex:
            context_parts.append(f"- Sex: {self.profile.sex}")
        if self.profile.activity_level is not None:
            level_desc = self._activity_level_description(self.profile.activity_level)
            context_parts.append(f"- Activity level: {level_desc}")
        if self.profile.dietary_preferences:
            context_parts.append(f"- Dietary preferences: {', '.join(self.profile.dietary_preferences)}")
        if self.profile.workout_preferences:
            context_parts.append(f"- Workout preferences: {', '.join(self.profile.workout_preferences)}")
        if self.profile.conditions:
            context_parts.append(f"- Health conditions: {', '.join(self.profile.conditions)}")
        if self.profile.cooking_time_per_day_minutes:
            context_parts.append(f"- Cooking time: {self.profile.cooking_time_per_day_minutes} minutes/day")
        if self.profile.meal_prep_preference:
            context_parts.append(f"- Meal prep preference: {self.profile.meal_prep_preference}")
        if self.profile.budget_per_week_usd:
            context_parts.append(f"- Budget: ${self.profile.budget_per_week_usd}/week")
        if self.profile.additional_context:
            for key, value in self.profile.additional_context.items():
                context_parts.append(f"- {key}: {value}")
        
        return "\n".join(context_parts)
    
    def _activity_level_description(self, level: float) -> str:
        """Convert activity level float to description."""
        if level < 0.2:
            return "Sedentary (little to no exercise)"
        elif level < 0.4:
            return "Lightly active (light exercise 1-3 days/week)"
        elif level < 0.6:
            return "Moderately active (moderate exercise 3-5 days/week)"
        elif level < 0.8:
            return "Very active (hard exercise 6-7 days/week)"
        else:
            return "Extremely active (very hard exercise, physical job, or training)"
    
    def _get_goals_context(self, goal_types: Optional[List[GoalType]] = None) -> str:
        """
        Build goals context string.
        
        Args:
            goal_types: Optional list of goal types to filter by. If None, includes all goals.
        """
        if not self.goals:
            return "No goals defined."
        
        # Filter goals if specific types requested
        relevant_goals = self.goals
        if goal_types:
            relevant_goals = [g for g in self.goals if g.goal_type in goal_types]
        
        if not relevant_goals:
            return "No relevant goals for this plan type."
        
        context_parts = ["User Goals:"]
        
        for goal in relevant_goals:
            goal_parts = [f"- **{goal.goal_type.value.replace('_', ' ').title()}**: {goal.description}"]
            
            if goal.target:
                target_str = f"  - Target: {goal.target}"
                if goal.target_value is not None:
                    target_str += f" = {goal.target_value}"
                goal_parts.append(target_str)
            
            if goal.target_date:
                goal_parts.append(f"  - Target date: {goal.target_date}")
            
            if goal.success_metrics:
                metrics_str = ", ".join([f"{k}: {v}" for k, v in goal.success_metrics.items()])
                goal_parts.append(f"  - Success metrics: {metrics_str}")
            
            context_parts.extend(goal_parts)
        
        return "\n".join(context_parts)
    
    def _get_goal_implications(self, goal_types: Optional[List[GoalType]] = None) -> str:
        """
        Analyze goals and generate specific implications for planning.
        
        This helps the LLM understand what the goals mean in practical terms.
        """
        if not self.goals:
            return ""
        
        relevant_goals = self.goals
        if goal_types:
            relevant_goals = [g for g in self.goals if g.goal_type in goal_types]
        
        if not relevant_goals:
            return ""
        
        implications = ["Goal Analysis and Implications:"]
        
        for goal in relevant_goals:
            if goal.goal_type == GoalType.WEIGHT_LOSS:
                implications.append(f"- Weight loss goal: Consider caloric deficit, high protein for satiety")
                if goal.target_value and self.profile and self.profile.weight_kg:
                    deficit = self.profile.weight_kg - goal.target_value
                    if deficit > 0:
                        implications.append(f"  - Target: Lose {deficit:.1f} kg")
            
            elif goal.goal_type == GoalType.WEIGHT_GAIN:
                implications.append(f"- Weight gain goal: Consider caloric surplus, adequate protein")
            
            elif goal.goal_type == GoalType.MUSCLE_GAIN:
                implications.append(f"- Muscle gain goal: High protein (1.6-2.2g/kg), progressive overload training")
            
            elif goal.goal_type == GoalType.ENDURANCE:
                implications.append(f"- Endurance goal: Adequate carbohydrates for energy, cardiovascular training")
            
            elif goal.goal_type == GoalType.BODY_FAT_PERCENTAGE:
                implications.append(f"- Body composition goal: Balance of resistance training and nutrition")
            
            elif goal.goal_type == GoalType.FLEXIBILITY:
                implications.append(f"- Flexibility goal: Include stretching and mobility work")
            
            elif goal.goal_type == GoalType.NUTRITION:
                implications.append(f"- Nutrition goal: Focus on food quality and balanced eating")
            
            elif goal.goal_type == GoalType.LONGEVITY:
                implications.append(f"- Longevity goal: Balanced approach, sustainable habits, variety")
            
            elif goal.goal_type == GoalType.GENERAL_FITNESS:
                implications.append(f"- General fitness goal: Balanced approach to exercise and nutrition")
        
        return "\n".join(implications)
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON from response, handling markdown code blocks."""
        response_text = response.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first and last lines if they're code block markers
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines)
        
        return json.loads(response_text)

