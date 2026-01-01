"""Chat service for orchestrating agent interactions."""
from dataclasses import dataclass
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.conversation import AgentType
from app.dao import UserDAO, ConversationDAO, MessageDAO
from app.services.chat.agent_router import AgentRouter
from app.services.agents import AgentResponse


@dataclass
class ChatResult:
    """Result of processing a chat message."""
    conversation_id: str
    user_message: Message
    assistant_message: Message
    metadata: dict


class ChatService:
    """Orchestrates chat flow and agent routing."""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_dao = UserDAO(db)
        self.conversation_dao = ConversationDAO(db)
        self.message_dao = MessageDAO(db)
    
    async def process_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        agent_type: Optional[str] = None
    ) -> ChatResult:
        """
        Process a chat message through the appropriate agent.
        
        Args:
            message: The user's message
            conversation_id: Optional existing conversation ID
            agent_type: Optional agent type override
            
        Returns:
            ChatResult with conversation info and messages
        """
        # Get or create user and conversation
        user = self.user_dao.get_or_create_temp_user()
        conversation = self.conversation_dao.get_or_create(user.id, conversation_id)
        
        # Save user message
        user_message = self.message_dao.create(conversation.id, "user", message)
        
        # Handle agent type override from frontend
        if agent_type:
            self._update_agent_if_valid(conversation, agent_type)
        
        # Get conversation history
        history = self.message_dao.get_by_conversation(conversation.id)
        
        # Process message with current agent
        router = AgentRouter(self.db, user.id)
        response = await self._process_with_transitions(
            router, conversation, message, history
        )
        
        # Save assistant message
        assistant_message = self.message_dao.create(
            conversation.id, "assistant", response.content
        )
        
        return ChatResult(
            conversation_id=conversation.id,
            user_message=user_message,
            assistant_message=assistant_message,
            metadata=response.metadata
        )
    
    async def _process_with_transitions(
        self,
        router: AgentRouter,
        conversation,
        message: str,
        history: List[Message]
    ) -> AgentResponse:
        """
        Process a message and handle any agent transitions.
        
        If an agent returns a transition, we update the conversation
        and optionally get a greeting from the new agent.
        """
        # Get current agent and process message
        agent = router.get_agent(conversation.agent_type)
        response = await agent.process(message, history)
        
        # Handle transitions (loop until no more transitions)
        while response.transition:
            # Update conversation to new agent
            self.conversation_dao.update_agent_type(
                conversation, response.transition.target_agent
            )
            
            if response.transition.get_greeting:
                # Get greeting from new agent, passing any context
                new_agent = router.get_agent(response.transition.target_agent)
                greeting = await new_agent.get_greeting(context=response.transition.context)
                
                # Combine current response with greeting
                combined_content = response.content
                if combined_content and greeting.content:
                    combined_content = f"{combined_content}\n\n{greeting.content}"
                elif greeting.content:
                    combined_content = greeting.content
                
                # Merge metadata and continue with greeting's transition (if any)
                response = AgentResponse(
                    content=combined_content,
                    metadata={**response.metadata, **greeting.metadata},
                    transition=greeting.transition  # Usually None for greetings
                )
            else:
                # No greeting needed, just update metadata
                response.metadata["agent_type"] = response.transition.target_agent.value
                break
        
        return response
    
    def _update_agent_if_valid(self, conversation, agent_type: str) -> None:
        """Update conversation agent type if valid."""
        try:
            requested_agent = AgentType(agent_type.lower())
            if conversation.agent_type != requested_agent:
                self.conversation_dao.update_agent_type(conversation, requested_agent)
        except ValueError:
            pass  # Ignore invalid agent types
