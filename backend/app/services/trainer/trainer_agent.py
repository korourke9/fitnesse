"""Trainer agent for workout tracking and fitness guidance."""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.conversation import AgentType
from app.models.message import Message
from app.services.agents import AgentResponse, Transition
from app.services.plan_generation import WorkoutPlanGenerator


class TrainerAgent:
    """Agent for tracking workouts and providing fitness guidance."""
    
    def __init__(self, db: Session, user_id: str, model_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.model_id = model_id
    
    async def process(self, message: str, history: List[Message]) -> AgentResponse:
        """Process a user message and return a response."""
        lower_msg = message.lower()
        
        # Check if user wants to switch to nutritionist
        if any(phrase in lower_msg for phrase in ["switch to nutritionist", "talk to nutritionist", "log meal", "log food"]):
            return AgentResponse(
                content="🥗 Switching you to our nutritionist...",
                metadata={"agent_type": AgentType.TRAINER.value},
                transition=Transition(AgentType.NUTRITIONIST, get_greeting=True)
            )
        
        # Check if user wants to go back to coordination
        if any(phrase in lower_msg for phrase in ["go back", "main menu", "what can i do", "help"]):
            return AgentResponse(
                content="",
                metadata={"agent_type": AgentType.TRAINER.value},
                transition=Transition(AgentType.COORDINATION, get_greeting=True)
            )
        
        # Check if this is a workout logging request (provide greeting-like response)
        if any(phrase in lower_msg for phrase in ["log workout", "log exercise", "talk to trainer", "workout", "exercise"]):
            return await self.get_greeting()
        
        # TODO: Implement full trainer agent with Bedrock
        # For now, provide a helpful placeholder response
        return AgentResponse(
            content=(
                f"💪 Nice work! I've logged: \"{message}\"\n\n"
                "(Full exercise tracking coming soon!)\n\n"
                "What else did you do, or say \"help\" for options."
            ),
            metadata={"agent_type": AgentType.TRAINER.value}
        )
    
    async def get_greeting(self, context: Dict[str, Any] = None) -> AgentResponse:
        """
        Get the agent's initial greeting.
        
        If context contains generate_plan=True, generates a workout plan first.
        """
        context = context or {}
        metadata = {"agent_type": AgentType.TRAINER.value}
        
        # Generate workout plan if requested
        if context.get("generate_plan"):
            try:
                generator = WorkoutPlanGenerator(db=self.db, user_id=self.user_id)
                plan = await generator.generate(duration_days=30)
                
                metadata["plan_id"] = plan.id
                metadata["workout_plan_generated"] = True
                
                return AgentResponse(
                    content=(
                        "💪 Your personalized workout plan is ready!\n\n"
                        "I'm your personal trainer and I'll help you track your workouts.\n\n"
                        "What did you do today? Describe your workout naturally, like:\n"
                        "• \"30 minutes on the treadmill\"\n"
                        "• \"Chest and back day - bench press, rows, pullups\"\n"
                        "• \"Yoga for 45 minutes\"\n"
                        "• \"10,000 steps today\""
                    ),
                    metadata=metadata
                )
            except Exception as e:
                print(f"Error generating workout plan: {str(e)}")
                return AgentResponse(
                    content=(
                        "I had trouble creating your workout plan. Let's try again - "
                        "just say \"create my workout plan\" and I'll get it sorted!"
                    ),
                    metadata=metadata
                )
        
        # Standard greeting (no plan generation)
        return AgentResponse(
            content=(
                "Hey! I'm your personal trainer. Let's track your workouts! 💪\n\n"
                "What did you do today? Describe your workout naturally, like:\n"
                "• \"30 minutes on the treadmill\"\n"
                "• \"Chest and back day - bench press, rows, pullups\"\n"
                "• \"Yoga for 45 minutes\"\n"
                "• \"10,000 steps today\""
            ),
            metadata=metadata
        )
