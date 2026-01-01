"""Coordination agent for routing users between different agents."""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.user_profile import UserProfile
from app.models.goal import Goal
from app.models.plan import Plan
from app.models.conversation import AgentType
from app.services.bedrock import BedrockService
from app.services.coordination.coordination_schema import CoordinationResponse
from app.services.agents import AgentResponse, Transition


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
    
    async def process(self, message: str, history: List[Message]) -> AgentResponse:
        """Process a user message and return a response."""
        response_text, suggested_agent, action = await self._get_llm_response(message, history)
        
        metadata = {
            "agent_type": AgentType.COORDINATION.value,
            "suggested_agent": suggested_agent,
            "action": action
        }
        
        # Handle actions - route to specialist agents with appropriate context
        if action == "generate_meal_plan":
            return AgentResponse(
                content="Let me connect you with our nutritionist to create your meal plan...",
                metadata=metadata,
                transition=Transition(
                    AgentType.NUTRITIONIST,
                    get_greeting=True,
                    context={"generate_plan": True}
                )
            )
        elif action == "generate_workout_plan":
            return AgentResponse(
                content="Let me connect you with our trainer to create your workout plan...",
                metadata=metadata,
                transition=Transition(
                    AgentType.TRAINER,
                    get_greeting=True,
                    context={"generate_plan": True}
                )
            )
        elif action == "route_to_nutritionist":
            return AgentResponse(
                content="",
                metadata=metadata,
                transition=Transition(AgentType.NUTRITIONIST, get_greeting=True)
            )
        elif action == "route_to_trainer":
            return AgentResponse(
                content="",
                metadata=metadata,
                transition=Transition(AgentType.TRAINER, get_greeting=True)
            )
        
        return AgentResponse(content=response_text, metadata=metadata)
    
    async def get_greeting(self, context: dict = None) -> AgentResponse:
        """Get the agent's initial greeting."""
        return AgentResponse(
            content=(
                "🎉 Great! I have everything I need to create your personalized plans. "
                "What would you like to do first?\n"
                "• Generate your meal plan\n"
                "• Generate your workout plan"
            ),
            metadata={"agent_type": AgentType.COORDINATION.value}
        )
    
    async def _get_llm_response(
        self,
        user_message: str,
        conversation_history: List[Message]
    ) -> tuple[str, Optional[str], Optional[str]]:
        """Get response from LLM."""
        messages = self._format_messages(conversation_history)
        messages.append({"role": "user", "content": user_message})
        
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
            print(f"Error in coordination agent: {str(e)}")
            import traceback
            traceback.print_exc()
            return (
                "I'm here to help! Would you like to generate a meal plan or workout plan?",
                None,
                None
            )
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for coordination agent."""
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
        
        return f"""You are a friendly front desk coordinator for Fitnesse, an AI-driven health and fitness application.

User Context:
{context}

Available Agents:
1. **Nutritionist Agent**: Helps users log meals and track nutrition
2. **Trainer Agent**: Helps users log exercises and track workouts

Guidelines:
- Be conversational and friendly
- If user wants to generate a meal plan, use action 'generate_meal_plan'
- If user wants to generate a workout plan, use action 'generate_workout_plan'
- If user wants to log meals (and has a meal plan), use action 'route_to_nutritionist'
- If user wants to log workouts (and has a workout plan), use action 'route_to_trainer'
- Keep responses concise (2-3 sentences)

Actions:
- "Create my meal plan" → action: 'generate_meal_plan'
- "Create my workout plan" → action: 'generate_workout_plan'
- "Log a meal" → action: 'route_to_nutritionist' (if they have a meal plan)
- "Log a workout" → action: 'route_to_trainer' (if they have a workout plan)"""
    
    def _format_messages(self, conversation_history: List[Message]) -> List[dict]:
        """Format conversation history for Bedrock."""
        messages = []
        for msg in conversation_history:
            role = "user" if msg.role == "user" else "assistant"
            messages.append({"role": role, "content": msg.content})
        return messages
