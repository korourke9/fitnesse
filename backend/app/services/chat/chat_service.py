"""Chat service for orchestrating agent interactions."""
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.conversation import AgentType
from app.dao import UserDAO, ConversationDAO, MessageDAO
from app.services.chat.agent_router import AgentRouter
from app.services.agents import AgentResponse
from app.services.bedrock import BedrockService
from app.services.nutritionist.logging.meal_logging_service import MealLoggingService
from app.services.trainer.logging.workout_logging_service import WorkoutLoggingService

# Phrase we put in assistant messages when asking user to confirm a log; used to detect "confirm?" context
CONFIRM_PROMPT_MARKER = "reply *yes* to save"


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
        Process a chat message. Uses conversation history + low-temp LLM to detect
        when the user is confirming a suggested meal/workout log; then re-parses
        the previous user message and saves. No pending state on the server.
        """
        user = self.user_dao.get_or_create_temp_user()
        conversation = self.conversation_dao.get_or_create(user.id, conversation_id)
        user_message = self.message_dao.create(conversation.id, "user", message)
        if agent_type:
            self._update_agent_if_valid(conversation, agent_type)

        history = self.message_dao.get_by_conversation(conversation.id)
        # Check if this might be a "confirm" reply: last assistant message was our confirm prompt
        if (
            conversation.agent_type in (AgentType.NUTRITIONIST, AgentType.TRAINER)
            and len(history) >= 3
        ):
            last_user = history[-1]
            last_assistant = history[-2]
            prev_user = history[-3]
            if (
                last_user.role == "user"
                and last_assistant.role == "assistant"
                and prev_user.role == "user"
                and (CONFIRM_PROMPT_MARKER in (last_assistant.content or "").lower())
            ):
                log_kind = "meal" if conversation.agent_type == AgentType.NUTRITIONIST else "workout"
                confirmed = await self._llm_user_confirmed_save(
                    last_assistant.content or "",
                    last_user.content or "",
                    log_kind=log_kind
                )
                if confirmed:
                    text_to_parse = (prev_user.content or "").strip()
                    if text_to_parse:
                        try:
                            logged_at = datetime.now(timezone.utc)
                            if log_kind == "meal":
                                svc = MealLoggingService(self.db)
                                parsed = svc.parse_meal(text_to_parse)
                                confirmed_data = parsed if isinstance(parsed, dict) else {}
                                svc.save_meal_log(text_to_parse, parsed, confirmed_data, logged_at=logged_at)
                            else:
                                svc = WorkoutLoggingService(self.db)
                                parsed = svc.parse_workout(text_to_parse)
                                confirmed_data = parsed if isinstance(parsed, dict) else {}
                                svc.save_workout_log(text_to_parse, parsed, confirmed_data, logged_at=logged_at)
                            assistant_message = self.message_dao.create(
                                conversation.id, "assistant", "Saved! Anything else you'd like to log or ask?"
                            )
                            return ChatResult(
                                conversation_id=conversation.id,
                                user_message=user_message,
                                assistant_message=assistant_message,
                                metadata={"agent_type": conversation.agent_type.value}
                            )
                        except Exception as e:
                            assistant_message = self.message_dao.create(
                                conversation.id, "assistant", f"Something went wrong saving that: {str(e)}. Try describing it again."
                            )
                            return ChatResult(
                                conversation_id=conversation.id,
                                user_message=user_message,
                                assistant_message=assistant_message,
                                metadata={"agent_type": conversation.agent_type.value}
                            )

        router = AgentRouter(self.db, user.id)
        response = await self._process_with_transitions(
            router, conversation, message, history
        )
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

    async def _llm_user_confirmed_save(
        self, last_assistant_content: str, user_reply: str, log_kind: str
    ) -> bool:
        """Use low-temp LLM to decide if the user's reply confirms they want to save the suggested log."""
        schema = {
            "type": "object",
            "properties": {"confirmed": {"type": "boolean"}},
            "required": ["confirmed"],
        }
        system = (
            "You determine whether the user confirmed they want to save a suggested log. "
            "Reply with JSON only: {\"confirmed\": true} or {\"confirmed\": false}. "
            "Treat as confirmed if they agree to save (e.g. yes, yep, save it, looks good, correct). "
            "Treat as not confirmed if they are correcting the log, asking a question, or declining."
        )
        content = (
            f"Assistant had just suggested a {log_kind} and asked the user to confirm. "
            f"Assistant said:\n{last_assistant_content}\n\nUser replied: {user_reply}\n\n"
            "Did the user confirm they want to save this log?"
        )
        try:
            bedrock = BedrockService()
            out = bedrock.invoke_structured(
                messages=[{"role": "user", "content": content}],
                output_schema=schema,
                system_prompt=system,
                max_tokens=64,
                temperature=0.1,
            )
            return bool(out.get("confirmed"))
        except Exception:
            return False
