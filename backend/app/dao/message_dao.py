"""Message Data Access Object."""
import uuid
from typing import List
from sqlalchemy.orm import Session
from app.models.message import Message


class MessageDAO:
    """Data access object for Message operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, conversation_id: str, role: str, content: str) -> Message:
        """Create a new message."""
        message = Message(
            id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            role=role,
            content=content
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message
    
    def get_by_conversation(self, conversation_id: str) -> List[Message]:
        """Get all messages for a conversation, ordered by creation time."""
        return self.db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()

