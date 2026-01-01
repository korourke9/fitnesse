"""Standardized agent response types."""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from app.models.conversation import AgentType


@dataclass
class Transition:
    """Represents a transition to another agent."""
    target_agent: AgentType
    get_greeting: bool = True  # Whether to immediately get greeting from target
    context: Dict[str, Any] = field(default_factory=dict)  # Context to pass to target agent


@dataclass
class AgentResponse:
    """Standardized response from any agent."""
    content: str
    metadata: dict = field(default_factory=dict)
    transition: Optional[Transition] = None  # If set, transition to another agent

