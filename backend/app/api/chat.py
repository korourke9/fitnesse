"""Chat API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.core.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, AgentType
from app.models.message import Message
from app.api.schemas.chat import ChatRequest, ChatResponse, MessageResponse
from app.services.onboarding_agent import OnboardingAgent

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/onboarding", response_model=ChatResponse)
async def chat_onboarding(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Handle onboarding chat messages.
    
    Creates a new conversation if conversation_id is not provided,
    otherwise continues the existing conversation.
    """
    # For now, we'll use a temporary user_id
    # TODO: Get from authentication
    temp_user_id = "temp-user-123"
    temp_user_email = "temp@fitnesse.local"
    
    # Get or create user
    user = db.query(User).filter(User.id == temp_user_id).first()
    if not user:
        user = User(
            id=temp_user_id,
            email=temp_user_email
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    user_id = user.id
    
    # Get or create conversation
    if request.conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == request.conversation_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        # Create new conversation
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            agent_type=AgentType.ONBOARDING
        )
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    
    # Save user message
    user_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        role="user",
        content=request.message
    )
    db.add(user_message)
    db.commit()
    
    # Get conversation history
    messages = db.query(Message).filter(
        Message.conversation_id == conversation.id
    ).order_by(Message.created_at).all()
    
    # Get agent response
    agent = OnboardingAgent(db=db)
    assistant_content = await agent.get_response(
        user_message=request.message,
        conversation_history=messages
    )
    
    # Save assistant message
    assistant_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        role="assistant",
        content=assistant_content
    )
    db.add(assistant_message)
    db.commit()
    db.refresh(assistant_message)
    
    return ChatResponse(
        conversation_id=conversation.id,
        user_message=MessageResponse(
            id=user_message.id,
            role=user_message.role,
            content=user_message.content,
            created_at=user_message.created_at
        ),
        assistant_message=MessageResponse(
            id=assistant_message.id,
            role=assistant_message.role,
            content=assistant_message.content,
            created_at=assistant_message.created_at
        )
    )

