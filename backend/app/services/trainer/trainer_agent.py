"""Trainer agent for workout tracking and fitness guidance."""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session

from app.models.conversation import AgentType
from app.models.message import Message
from app.services.agents import AgentResponse, Transition
from app.services.trainer.planning import WorkoutPlanGenerator, WorkoutPlanData
from app.services.bedrock import BedrockService
from app.services.trainer.logging.workout_logging_service import WorkoutLoggingService
from app.dao import PlanDAO
from app.models.plan import PlanType


class TrainerAgent:
    """Agent for tracking workouts and providing fitness guidance."""
    
    def __init__(self, db: Session, user_id: str, model_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.model_id = model_id
        self.bedrock = BedrockService(model_id=model_id)
        self.plan_dao = PlanDAO(db)
    
    async def process(self, message: str, history: List[Message]) -> AgentResponse:
        """Process a user message and return a response."""
        lower_msg = message.strip().lower()
        
        # Check if user wants to switch to nutritionist
        if any(phrase in lower_msg for phrase in ["switch to nutritionist", "talk to nutritionist", "log meal", "log food"]):
            return AgentResponse(
                content="🥗 Switching you to our nutritionist...",
                metadata={"agent_type": AgentType.TRAINER.value},
                transition=Transition(AgentType.NUTRITIONIST, get_greeting=True)
            )
        
        # In-chat workout logging: use LLM to decide if user is describing a workout they want to log
        if await self._llm_is_workout_log(message, history):
            try:
                workout_svc = WorkoutLoggingService(self.db)
                parsed = workout_svc.parse_workout(message)
                conf = parsed.get("confidence", 0)
                norm = (parsed.get("normalized_text") or "").strip()
                if conf >= 0.4 and norm:
                    summary = self._format_workout_summary(parsed)
                    return AgentResponse(
                        content=f"{summary}\n\nReply *yes* to save, or tell me what to change.",
                        metadata={"agent_type": AgentType.TRAINER.value}
                    )
            except Exception:
                pass  # Fall through to conversational response
        return await self._get_llm_response(message, history)
    
    async def _get_llm_response(self, message: str, history: List[Message]) -> AgentResponse:
        """Get intelligent response from Bedrock."""
        # Build context about user's workout plan so the LLM can reference it
        workout_plan = self.plan_dao.get_active_plan(self.user_id, PlanType.WORKOUT)
        plan_context = ""
        if workout_plan:
            try:
                workout_model = WorkoutPlanData.from_stored(workout_plan.plan_data)
                end_text = f", end: {workout_plan.end_date}" if workout_plan.end_date else " (ongoing)"
                parts = [f"User has an active workout plan (start: {workout_plan.start_date}{end_text})."]
                if workout_model.workouts_per_week is not None:
                    parts.append(f"Target: {workout_model.workouts_per_week} workouts per week.")
                if workout_model.notes:
                    parts.append(f"Notes: {workout_model.notes}")
                plan_context = " ".join(parts) + "\n\n"
            except Exception:
                # Fallback if plan_data is malformed
                end_text = f", end: {workout_plan.end_date}" if workout_plan.end_date else " (ongoing)"
                plan_context = f"User has an active workout plan (start: {workout_plan.start_date}{end_text}).\n\n"

        system_prompt = f"""You are a friendly personal trainer. Reply directly to what the user said. Do NOT respond with a generic menu like "You can: Log workouts / Ask questions / Give feedback" or "What would you like to do?" — only give that if they literally ask "what can you do?" or "help".

{plan_context}

Your role: help them log workouts, answer questions about their plan, and handle feedback (e.g. "I prefer dumbbells", "I can only train 3 days"). Be specific and actionable. If they say "hi" or "hey", greet them briefly and invite them to log a workout or ask something. If they ask about their plan, use the context above if relevant.

If their message is about meals/nutrition (not workouts), reply naturally and add: [Go to Nutrition page](/nutrition). Use markdown links [text](/path). Paths: /nutrition, /training, /goals, /dashboard. For "help" or "go back", suggest [Go to Dashboard](/dashboard). Do not switch agents—only provide links.

Keep responses to 2-4 sentences. Be conversational and useful."""

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
            
            # Check if response suggests redirecting to nutritionist - if it includes a link to /nutrition, don't transition
            # (let the link handle navigation instead)
            # Only transition if explicitly requested without a link
            if "nutritionist" in response_text.lower() and ("connect" in response_text.lower() or "switch" in response_text.lower()) and "/nutrition" not in response_text:
                return AgentResponse(
                    content=response_text,
                    metadata={"agent_type": AgentType.TRAINER.value},
                    transition=Transition(AgentType.NUTRITIONIST, get_greeting=True)
                )
            
            return AgentResponse(
                content=response_text,
                metadata={"agent_type": AgentType.TRAINER.value}
            )
        except Exception as e:
            print(f"Error in trainer agent Bedrock call: {str(e)}")
            # Contextual fallback so the user still gets a useful reply
            lower = (message or "").strip().lower()
            fallback = (
                "💪 I'm having a quick connection hiccup. Ask me again in a moment."
            )
            return AgentResponse(
                content=fallback,
                metadata={"agent_type": AgentType.TRAINER.value}
            )
    
    async def get_greeting(self, context: Dict[str, Any] = None) -> AgentResponse:
        """
        Get the agent's initial greeting.
        
        If context contains generate_plan=True, generates a workout plan first.
        """
        context = context or {}
        metadata = {"agent_type": AgentType.TRAINER.value}
        
        # Generate workout plan if requested
        if context.get("generate_plan"):
            try:
                generator = WorkoutPlanGenerator(db=self.db, user_id=self.user_id)
                plan = await generator.generate(duration_days=30)
                
                metadata["plan_id"] = plan.id
                metadata["workout_plan_generated"] = True
                
                return AgentResponse(
                    content=(
                        "💪 Your personalized workout plan is ready!\n\n"
                        "I'm your personal trainer and I'll help you track your workouts.\n\n"
                        "What did you do today? Describe your workout naturally, like:\n"
                        "• \"30 minutes on the treadmill\"\n"
                        "• \"Chest and back day - bench press, rows, pullups\"\n"
                        "• \"Yoga for 45 minutes\"\n"
                        "• \"10,000 steps today\""
                    ),
                    metadata=metadata
                )
            except Exception as e:
                print(f"Error generating workout plan: {str(e)}")
                return AgentResponse(
                    content=(
                        "I had trouble creating your workout plan. Let's try again - "
                        "just say \"create my workout plan\" and I'll get it sorted!"
                    ),
                    metadata=metadata
                )
        
        # Standard greeting (no plan generation)
        return AgentResponse(
            content=(
                "Hey! I'm your personal trainer. Let's track your workouts! 💪\n\n"
                "What did you do today? Describe your workout naturally, like:\n"
                "• \"30 minutes on the treadmill\"\n"
                "• \"Chest and back day - bench press, rows, pullups\"\n"
                "• \"Yoga for 45 minutes\"\n"
                "• \"10,000 steps today\""
            ),
            metadata=metadata
        )

    async def _llm_is_workout_log(self, message: str, history: List[Message]) -> bool:
        """Use low-temp LLM to decide if the user is describing a workout they want to log (vs question/feedback/other)."""
        schema = {
            "type": "object",
            "properties": {"log_workout": {"type": "boolean"}},
            "required": ["log_workout"],
        }
        system = (
            "You determine whether the user is describing a workout or exercise they just did and want to log. "
            "Reply with JSON only: {\"log_workout\": true} or {\"log_workout\": false}. "
            "Set log_workout true when they are telling you what they did (e.g. '30 min run', 'bench 3x8', 'yoga for 45 min'). "
            "Set log_workout false when they are asking a question, giving feedback about their plan, asking for help, or discussing something else."
        )
        recent = ""
        if history:
            for msg in history[-4:]:
                recent += f"{msg.role}: {msg.content or ''}\n"
        content = f"Recent conversation:\n{recent}\nUser message: {message}\n\nIs the user describing a workout they want to log?"
        try:
            out = self.bedrock.invoke_structured(
                messages=[{"role": "user", "content": content}],
                output_schema=schema,
                system_prompt=system,
                max_tokens=32,
                temperature=0.1,
            )
            return bool(out.get("log_workout"))
        except Exception:
            return False

    @staticmethod
    def _format_workout_summary(parsed: Dict[str, Any]) -> str:
        parts = [parsed.get("normalized_text", "Workout")]
        if parsed.get("total_duration_minutes") is not None:
            parts.append(f"~{int(parsed['total_duration_minutes'])} min")
        if parsed.get("estimated_calories_burned") is not None:
            parts.append(f"~{int(parsed['estimated_calories_burned'])} cal")
        return "💪 " + " — ".join(parts)
