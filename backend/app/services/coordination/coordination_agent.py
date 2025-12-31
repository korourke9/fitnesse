"""Coordination agent for routing users between different agents."""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.user_profile import UserProfile
from app.models.goal import Goal
from app.models.plan import Plan
from app.services.bedrock import BedrockService
from app.services.coordination.coordination_schema import CoordinationResponse
from app.core.config import settings


class CoordinationAgent:
    """Agent for coordinating user interactions and routing to appropriate agents."""
    
    @property
    def response_schema(self) -> dict:
        """Get JSON schema from Pydantic model."""
        return CoordinationResponse.model_json_schema(mode='serialization')
    
    def __init__(self, db: Session, user_id: str, model_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.bedrock = BedrockService(model_id=model_id)
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for coordination agent."""
        # Load user context
        profile = self.db.query(UserProfile).filter(UserProfile.user_id == self.user_id).first()
        goals = self.db.query(Goal).filter(Goal.user_id == self.user_id, Goal.is_active == True).all()
        active_plan = self.db.query(Plan).filter(
            Plan.user_id == self.user_id,
            Plan.is_active == True
        ).first()
        
        context_parts = []
        
        if profile:
            context_parts.append("User Profile:")
            if profile.height_cm:
                context_parts.append(f"- Height: {profile.height_cm} cm")
            if profile.weight_kg:
                context_parts.append(f"- Weight: {profile.weight_kg} kg")
            if profile.age:
                context_parts.append(f"- Age: {profile.age}")
            if profile.dietary_preferences:
                context_parts.append(f"- Dietary preferences: {', '.join(profile.dietary_preferences)}")
            if profile.workout_preferences:
                context_parts.append(f"- Workout preferences: {', '.join(profile.workout_preferences)}")
        
        if goals:
            context_parts.append("\nActive Goals:")
            for goal in goals:
                context_parts.append(f"- {goal.description} (target: {goal.target})")
        
        # Plan status section
        context_parts.append("\nPlan Status:")
        has_meal_plan = active_plan and active_plan.plan_data and active_plan.plan_data.get("diet")
        has_workout_plan = active_plan and active_plan.plan_data and active_plan.plan_data.get("exercise")
        
        if has_meal_plan:
            context_parts.append("- ✅ Meal plan: CREATED - user can log meals with nutritionist")
        else:
            context_parts.append("- ❌ Meal plan: NOT CREATED - user should generate it first")
        
        if has_workout_plan:
            context_parts.append("- ✅ Workout plan: CREATED - user can log workouts with trainer")
        else:
            context_parts.append("- ❌ Workout plan: NOT CREATED - user should generate it first")
        
        context = "\n".join(context_parts) if context_parts else "No user profile or goals yet."
        
        return f"""You are a friendly front desk coordinator for Fitnesse, an AI-driven health and fitness application. Your role is to help users navigate the application and connect them with the right specialist agents.

User Context:
{context}

Available Agents:
1. **Nutritionist Agent**: Helps users log meals, track nutrition, estimate macros/calories, and provides nutrition guidance
2. **Trainer Agent**: Helps users log exercises, track workouts, and provides fitness guidance

Your Responsibilities:
- Greet users warmly and understand what they want to do
- Help users generate their personalized plans (meal plan, workout plan)
- Route users to the appropriate agent (nutritionist for meals, trainer for workouts)
- Show users their plans if they ask
- Answer general questions about the app

Guidelines:
- Be conversational, friendly, and helpful
- Don't be pushy - let users choose what they want to do
- If user wants to generate a meal plan, use action 'generate_meal_plan'
- If user wants to generate a workout plan, use action 'generate_workout_plan'
- If user wants to log meals (and already has a meal plan), use action 'route_to_nutritionist'
- If user wants to log workouts (and already has a workout plan), use action 'route_to_trainer'
- If user wants to see their meal plan, use action 'show_meal_plan'
- If user wants to see their workout plan, use action 'show_workout_plan'
- Keep responses concise (2-3 sentences)

When to take action:
- "Create my meal plan" / "Generate nutrition plan" → action: 'generate_meal_plan'
- "Create my workout plan" / "Generate exercise plan" → action: 'generate_workout_plan'
- "Log a meal" / "Track food" / "What I ate" → action: 'route_to_nutritionist' (if they have a meal plan) or suggest generating one first
- "Log a workout" / "Track exercise" → action: 'route_to_trainer' (if they have a workout plan) or suggest generating one first
- "Show my meal plan" / "What should I eat" → action: 'show_meal_plan'
- "Show my workout plan" / "What exercises" → action: 'show_workout_plan'
- General questions / "What can I do?" → Stay here and explain options

Always be helpful and guide users naturally to the right place."""
    
    def _format_messages(self, conversation_history: List[Message]) -> List[dict]:
        """Format conversation history for Bedrock."""
        messages = []
        for msg in conversation_history:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({
                "role": role,
                "content": msg.content
            })
        return messages
    
    async def get_response(
        self,
        user_message: str,
        conversation_history: List[Message]
    ) -> tuple[str, Optional[str], Optional[str]]:
        """
        Generate a response and determine routing.
        
        Returns:
            Tuple of (response_text, suggested_agent, action)
            - response_text: The conversational response
            - suggested_agent: 'nutritionist' or 'trainer' if routing, None otherwise
            - action: 'route_to_nutritionist', 'route_to_trainer', 'show_plan', 'stay_here', or None
        """
        messages = self._format_messages(conversation_history)
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        system_prompt = self._build_system_prompt()
        
        try:
            response = self.bedrock.invoke_structured(
                messages=messages,
                system_prompt=system_prompt,
                output_schema=self.response_schema
            )
            
            coordination_response = CoordinationResponse(**response)
            
            return (
                coordination_response.response,
                coordination_response.suggested_agent,
                coordination_response.action
            )
        except Exception as e:
            # Log the error for debugging
            print(f"Error in coordination agent: {str(e)}")
            import traceback
            traceback.print_exc()
            # Fallback response on error
            return (
                "I'm here to help you navigate Fitnesse! Would you like to log a meal with our nutritionist, or log a workout with our trainer?",
                None,
                None
            )

