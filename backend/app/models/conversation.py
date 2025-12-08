"""Conversation model."""
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


class AgentType(str, enum.Enum):
    """Agent type enumeration."""
    ONBOARDING = "onboarding"
    NUTRITIONIST = "nutritionist"
    TRAINER = "trainer"
    ANALYTICS = "analytics"


class Conversation(Base):
    """Conversation model."""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    agent_type = Column(SQLEnum(AgentType), nullable=False, default=AgentType.ONBOARDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

