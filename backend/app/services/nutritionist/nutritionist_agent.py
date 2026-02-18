"""Nutritionist agent for meal tracking and nutrition guidance."""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.conversation import AgentType
from app.models.message import Message
from app.services.agents import AgentResponse, Transition
from app.services.plan_generation import MealPlanGenerator
from app.services.bedrock import BedrockService
from app.services.nutritionist.logging.meal_logging_service import MealLoggingService
from app.dao import PlanDAO
from app.models.plan import PlanType


class NutritionistAgent:
    """Agent for tracking meals and providing nutrition guidance."""
    
    def __init__(self, db: Session, user_id: str, model_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.model_id = model_id
        self.bedrock = BedrockService(model_id=model_id)
        self.plan_dao = PlanDAO(db)
    
    async def process(self, message: str, history: List[Message]) -> AgentResponse:
        """Process a user message and return a response."""
        lower_msg = message.strip().lower()
        
        # Check if user wants to switch to trainer
        if any(phrase in lower_msg for phrase in ["switch to trainer", "talk to trainer", "log workout", "log exercise"]):
            return AgentResponse(
                content="💪 Switching you to our trainer...",
                metadata={"agent_type": AgentType.NUTRITIONIST.value},
                transition=Transition(AgentType.TRAINER, get_greeting=True)
            )
        
        # In-chat meal logging: use LLM to decide if user is describing a meal they want to log
        if await self._llm_is_meal_log(message, history):
            try:
                meal_svc = MealLoggingService(self.db)
                parsed = meal_svc.parse_meal(message)
                conf = parsed.get("confidence", 0)
                norm = (parsed.get("normalized_text") or "").strip()
                if conf >= 0.4 and norm:
                    summary = self._format_meal_summary(parsed)
                    return AgentResponse(
                        content=f"{summary}\n\nReply *yes* to save, or tell me what to change.",
                        metadata={"agent_type": AgentType.NUTRITIONIST.value}
                    )
            except Exception:
                pass  # Fall through to conversational response
        return await self._get_llm_response(message, history)
    
    async def _get_llm_response(self, message: str, history: List[Message]) -> AgentResponse:
        """Get intelligent response from Bedrock."""
        # Build context about user's meal plan
        meal_plan = self.plan_dao.get_active_plan(self.user_id, PlanType.MEAL)
        plan_context = ""
        if meal_plan and isinstance(meal_plan.plan_data, dict):
            plan_summary = f"User has an active meal plan (start: {meal_plan.start_date}, end: {meal_plan.end_date}). "
            plan_context = plan_summary
        
        system_prompt = f"""You are a friendly and helpful nutritionist assistant helping users with their meal plans and nutrition tracking.

{plan_context}

Your role:
- Help users log meals and track nutrition
- Answer questions about their meal plan
- Handle feedback about their meal plan (e.g., "I don't like breakfast", "I need more protein")
- Provide nutrition guidance

IMPORTANT: If the user's message is clearly about workouts or exercise (not nutrition), respond naturally and include a markdown-style link: "This seems more suited for our trainer. [Go to Training page](/training)" 

Use markdown-style links [text](/path) for navigation suggestions. Available paths: /training (for workout-related topics), /nutrition (for meal-related topics), /goals (for goals and check-ins), /dashboard (for main hub). For "help" or "go back", suggest [Go to Dashboard](/dashboard) or [Goals](/goals); do not switch the user to another agent—only provide links.

Keep responses conversational, helpful, and brief (2-3 sentences max). If they're giving feedback about their plan, acknowledge it and let them know you'll consider it for future updates."""

        # Format conversation history
        messages = []
        for msg in history[-5:]:  # Last 5 messages for context
            messages.append({"role": msg.role, "content": msg.content})
        messages.append({"role": "user", "content": message})
        
        try:
            response_text = self.bedrock.invoke(
                messages=messages,
                system_prompt=system_prompt,
                max_tokens=500,
                temperature=0.2
            )
            
            # Check if response suggests redirecting to trainer - if it includes a link to /training, don't transition
            # (let the link handle navigation instead)
            # Only transition if explicitly requested without a link
            if "trainer" in response_text.lower() and ("connect" in response_text.lower() or "switch" in response_text.lower()) and "/training" not in response_text:
                return AgentResponse(
                    content=response_text,
                    metadata={"agent_type": AgentType.NUTRITIONIST.value},
                    transition=Transition(AgentType.TRAINER, get_greeting=True)
                )
            
            return AgentResponse(
                content=response_text,
                metadata={"agent_type": AgentType.NUTRITIONIST.value}
            )
        except Exception as e:
            print(f"Error in nutritionist agent Bedrock call: {str(e)}")
            fallback = (
                "🥗 I'm having a quick connection hiccup. Ask me again in a moment."
            )
            return AgentResponse(
                content=fallback,
                metadata={"agent_type": AgentType.NUTRITIONIST.value}
            )
    
    async def get_greeting(self, context: Dict[str, Any] = None) -> AgentResponse:
        """
        Get the agent's initial greeting.
        
        If context contains generate_plan=True, generates a meal plan first.
        """
        context = context or {}
        metadata = {"agent_type": AgentType.NUTRITIONIST.value}
        
        # Generate meal plan if requested
        if context.get("generate_plan"):
            try:
                generator = MealPlanGenerator(db=self.db, user_id=self.user_id)
                plan = await generator.generate(duration_days=30)
                
                metadata["plan_id"] = plan.id
                metadata["meal_plan_generated"] = True
                
                return AgentResponse(
                    content=(
                        "🍽️ Your personalized meal plan is ready!\n\n"
                        "I'm your nutritionist and I'll help you track your meals and nutrition.\n\n"
                        "What did you eat? You can describe your meal naturally, like:\n"
                        "• \"I had eggs and toast for breakfast\"\n"
                        "• \"Chicken salad with avocado for lunch\"\n"
                        "• \"A protein shake after my workout\""
                    ),
                    metadata=metadata
                )
            except Exception as e:
                print(f"Error generating meal plan: {str(e)}")
                return AgentResponse(
                    content=(
                        "I had trouble creating your meal plan. Let's try again - "
                        "just say \"create my meal plan\" and I'll get it sorted!"
                    ),
                    metadata=metadata
                )
        
        # Standard greeting (no plan generation)
        return AgentResponse(
            content=(
                "Hi! I'm your nutritionist. I'll help you track your meals and nutrition. 🥗\n\n"
                "What did you eat? You can describe your meal naturally, like:\n"
                "• \"I had eggs and toast for breakfast\"\n"
                "• \"Chicken salad with avocado for lunch\"\n"
                "• \"A protein shake after my workout\""
            ),
            metadata=metadata
        )

    async def _llm_is_meal_log(self, message: str, history: List[Message]) -> bool:
        """Use low-temp LLM to decide if the user is describing a meal they want to log (vs question/feedback/other)."""
        schema = {
            "type": "object",
            "properties": {"log_meal": {"type": "boolean"}},
            "required": ["log_meal"],
        }
        system = (
            "You determine whether the user is describing a meal or food they just ate and want to log. "
            "Reply with JSON only: {\"log_meal\": true} or {\"log_meal\": false}. "
            "Set log_meal true when they are telling you what they ate (e.g. 'I had chicken salad', 'eggs and toast for breakfast'). "
            "Set log_meal false when they are asking a question, giving feedback about their plan, asking for help, or discussing something else."
        )
        recent = ""
        if history:
            for msg in history[-4:]:
                recent += f"{msg.role}: {msg.content or ''}\n"
        content = f"Recent conversation:\n{recent}\nUser message: {message}\n\nIs the user describing a meal they want to log?"
        try:
            out = self.bedrock.invoke_structured(
                messages=[{"role": "user", "content": content}],
                output_schema=schema,
                system_prompt=system,
                max_tokens=32,
                temperature=0.1,
            )
            return bool(out.get("log_meal"))
        except Exception:
            return False

    @staticmethod
    def _format_meal_summary(parsed: Dict[str, Any]) -> str:
        parts = [parsed.get("normalized_text", "Meal")]
        est = parsed.get("estimate") or {}
        if isinstance(est, dict) and est.get("calories") is not None:
            parts.append(f"~{int(est['calories'])} cal")
        return "🥗 " + " — ".join(parts)
