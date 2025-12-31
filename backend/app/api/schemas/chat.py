"""Chat-related schemas."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class MessageCreate(BaseModel):
    """Schema for creating a message."""
    content: str
    conversation_id: Optional[str] = None


class MessageResponse(BaseModel):
    """Schema for message response."""
    id: str
    role: str
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    """Schema for conversation response."""
    id: str
    user_id: str
    agent_type: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    """Schema for chat request."""
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Schema for chat response."""
    conversation_id: str
    user_message: MessageResponse
    assistant_message: MessageResponse
    metadata: Optional[dict] = None  # For completion status, plan_id, routing info, etc.

