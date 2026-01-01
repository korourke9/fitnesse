"""Nutritionist agent for meal tracking and nutrition guidance."""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.conversation import AgentType
from app.models.message import Message
from app.services.agents import AgentResponse, Transition
from app.services.plan_generation import MealPlanGenerator


class NutritionistAgent:
    """Agent for tracking meals and providing nutrition guidance."""
    
    def __init__(self, db: Session, user_id: str, model_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.model_id = model_id
    
    async def process(self, message: str, history: List[Message]) -> AgentResponse:
        """Process a user message and return a response."""
        lower_msg = message.lower()
        
        # Check if user wants to switch to trainer
        if any(phrase in lower_msg for phrase in ["switch to trainer", "talk to trainer", "log workout", "log exercise"]):
            return AgentResponse(
                content="💪 Switching you to our trainer...",
                metadata={"agent_type": AgentType.NUTRITIONIST.value},
                transition=Transition(AgentType.TRAINER, get_greeting=True)
            )
        
        # Check if user wants to go back to coordination
        if any(phrase in lower_msg for phrase in ["go back", "main menu", "what can i do", "help"]):
            return AgentResponse(
                content="",
                metadata={"agent_type": AgentType.NUTRITIONIST.value},
                transition=Transition(AgentType.COORDINATION, get_greeting=True)
            )
        
        # Check if this is a meal logging request (provide greeting-like response)
        if any(phrase in lower_msg for phrase in ["log meal", "log food", "talk to nutritionist", "nutrition"]):
            return await self.get_greeting()
        
        # TODO: Implement full nutritionist agent with Bedrock
        # For now, provide a helpful placeholder response
        return AgentResponse(
            content=(
                f"🥗 Got it! I've logged: \"{message}\"\n\n"
                "(Full calorie/macro tracking coming soon!)\n\n"
                "What else did you eat, or say \"help\" for options."
            ),
            metadata={"agent_type": AgentType.NUTRITIONIST.value}
        )
    
    async def get_greeting(self, context: Dict[str, Any] = None) -> AgentResponse:
        """
        Get the agent's initial greeting.
        
        If context contains generate_plan=True, generates a meal plan first.
        """
        context = context or {}
        metadata = {"agent_type": AgentType.NUTRITIONIST.value}
        
        # Generate meal plan if requested
        if context.get("generate_plan"):
            try:
                generator = MealPlanGenerator(db=self.db, user_id=self.user_id)
                plan = await generator.generate(duration_days=30)
                
                metadata["plan_id"] = plan.id
                metadata["meal_plan_generated"] = True
                
                return AgentResponse(
                    content=(
                        "🍽️ Your personalized meal plan is ready!\n\n"
                        "I'm your nutritionist and I'll help you track your meals and nutrition.\n\n"
                        "What did you eat? You can describe your meal naturally, like:\n"
                        "• \"I had eggs and toast for breakfast\"\n"
                        "• \"Chicken salad with avocado for lunch\"\n"
                        "• \"A protein shake after my workout\""
                    ),
                    metadata=metadata
                )
            except Exception as e:
                print(f"Error generating meal plan: {str(e)}")
                return AgentResponse(
                    content=(
                        "I had trouble creating your meal plan. Let's try again - "
                        "just say \"create my meal plan\" and I'll get it sorted!"
                    ),
                    metadata=metadata
                )
        
        # Standard greeting (no plan generation)
        return AgentResponse(
            content=(
                "Hi! I'm your nutritionist. I'll help you track your meals and nutrition. 🥗\n\n"
                "What did you eat? You can describe your meal naturally, like:\n"
                "• \"I had eggs and toast for breakfast\"\n"
                "• \"Chicken salad with avocado for lunch\"\n"
                "• \"A protein shake after my workout\""
            ),
            metadata=metadata
        )
