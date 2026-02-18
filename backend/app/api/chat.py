"""Chat API endpoint."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dao import ConversationDAO, MessageDAO
from app.api.schemas.chat import ChatRequest, ChatResponse, MessageResponse
from app.services.chat import ChatService

router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/chat/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    """Return all messages for a conversation (for loading history)."""
    conversation_dao = ConversationDAO(db)
    message_dao = MessageDAO(db)
    conversation = conversation_dao.get_by_id(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = message_dao.get_by_conversation(conversation_id)
    return {
        "conversation_id": conversation_id,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content or "",
                "created_at": m.created_at,
            }
            for m in messages
        ],
    }


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Unified chat endpoint with internal agent routing.
    
    The backend tracks which agent is active via conversation.agent_type
    and routes messages to the appropriate agent automatically.
    
    Agent transitions happen server-side based on:
    - Onboarding completion → Coordination
    - User intent to switch agents
    - Explicit routing actions
    
    Response includes current agent_type so frontend can display appropriate UI.
    """
    service = ChatService(db)
    
    try:
        result = await service.process_message(
            message=request.message,
            conversation_id=request.conversation_id,
            agent_type=request.agent_type
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return ChatResponse(
        conversation_id=result.conversation_id,
        user_message=MessageResponse(
            id=result.user_message.id,
            role=result.user_message.role,
            content=result.user_message.content,
            created_at=result.user_message.created_at
        ),
        assistant_message=MessageResponse(
            id=result.assistant_message.id,
            role=result.assistant_message.role,
            content=result.assistant_message.content,
            created_at=result.assistant_message.created_at
        ),
        metadata=result.metadata
    )
