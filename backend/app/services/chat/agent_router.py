"""Agent router - factory for getting agent instances."""
from typing import Protocol
from sqlalchemy.orm import Session

from app.models.conversation import AgentType
from app.services.agents import AgentResponse


class Agent(Protocol):
    """Protocol defining the agent interface."""
    
    async def process(self, message: str, history: list) -> AgentResponse:
        """Process a user message and return a response."""
        ...
    
    async def get_greeting(self) -> AgentResponse:
        """Get the agent's initial greeting."""
        ...


class AgentRouter:
    """Factory for creating agent instances. Routes AgentType → Agent."""
    
    def __init__(self, db: Session, user_id: str):
        self.db = db
        self.user_id = user_id
    
    def get_agent(self, agent_type: AgentType) -> Agent:
        """Get the agent instance for the given type."""
        # Import here to avoid circular imports
        from app.services.onboarding import OnboardingAgent
        from app.services.coordination import CoordinationAgent
        from app.services.nutritionist import NutritionistAgent
        from app.services.trainer import TrainerAgent
        
        agents = {
            AgentType.ONBOARDING: OnboardingAgent,
            AgentType.COORDINATION: CoordinationAgent,
            AgentType.NUTRITIONIST: NutritionistAgent,
            AgentType.TRAINER: TrainerAgent,
        }
        
        agent_class = agents.get(agent_type, CoordinationAgent)
        return agent_class(db=self.db, user_id=self.user_id)
