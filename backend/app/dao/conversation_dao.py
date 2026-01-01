"""Conversation Data Access Object."""
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.models.conversation import Conversation, AgentType


class ConversationDAO:
    """Data access object for Conversation operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Get conversation by ID."""
        return self.db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
    
    def create(self, user_id: str, agent_type: AgentType = AgentType.ONBOARDING) -> Conversation:
        """Create a new conversation."""
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            agent_type=agent_type
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation
    
    def get_or_create(self, user_id: str, conversation_id: Optional[str] = None) -> Conversation:
        """Get existing conversation or create a new one."""
        if conversation_id:
            conversation = self.get_by_id(conversation_id)
            if conversation:
                return conversation
        return self.create(user_id)
    
    def update_agent_type(self, conversation: Conversation, agent_type: AgentType) -> None:
        """Update the agent type for a conversation."""
        conversation.agent_type = agent_type
        self.db.commit()

