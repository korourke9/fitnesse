"""Onboarding agent for conversational data collection."""
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.user_profile import UserProfile
from app.models.goal import Goal, GoalType
from app.models.conversation import AgentType
from app.services.bedrock import BedrockService
from app.services.onboarding.onboarding_schema import OnboardingResponse
from app.services.agents import AgentResponse, Transition
from app.core.config import settings


class OnboardingAgent:
    """Agent for handling onboarding conversations with AWS Bedrock."""
    
    @property
    def response_schema(self) -> Dict[str, Any]:
        """Get JSON schema from Pydantic model."""
        return OnboardingResponse.model_json_schema(mode='serialization')
    
    def __init__(self, db: Session, user_id: str, model_id: Optional[str] = None):
        self.db = db
        self.user_id = user_id
        self.bedrock = BedrockService(model_id=model_id)
        
        # Load existing profile and goals for context
        self.existing_profile = self.db.query(UserProfile).filter(
            UserProfile.user_id == self.user_id
        ).first()
        
        self.existing_goals = self.db.query(Goal).filter(
            Goal.user_id == self.user_id,
            Goal.is_active == True
        ).all()
        
        # Build system prompt with context about existing data
        self.system_prompt = self._build_system_prompt()
    
    async def process(self, message: str, history: List[Message]) -> AgentResponse:
        """Process a user message and return a response."""
        response_text, is_complete = await self._get_llm_response(message, history)
        
        metadata = {"agent_type": AgentType.ONBOARDING.value}
        
        if is_complete:
            metadata["is_complete"] = True
            return AgentResponse(
                content=response_text,
                metadata=metadata,
                transition=Transition(AgentType.COORDINATION, get_greeting=True)
            )
        
        return AgentResponse(content=response_text, metadata=metadata)
    
    async def get_greeting(self, context: dict = None) -> AgentResponse:
        """Get the agent's initial greeting."""
        return AgentResponse(
            content=(
                "Hi! I'm your health assistant. I'm here to help you create a personalized "
                "fitness and nutrition plan. 👋\n\n"
                "To get started, could you tell me a bit about yourself? "
                "What are your main health or fitness goals?"
            ),
            metadata={"agent_type": AgentType.ONBOARDING.value}
        )
    
    async def _get_llm_response(
        self,
        user_message: str,
        conversation_history: List[Message]
    ) -> tuple[str, bool]:
        """
        Generate a response using AWS Bedrock.
        
        Returns:
            Tuple of (response_text, is_complete)
        """
        messages = self._format_messages(conversation_history)
        
        try:
            response_data = self.bedrock.invoke_structured(
                messages=messages,
                output_schema=self.response_schema,
                system_prompt=self.system_prompt,
                max_tokens=2048,
                temperature=0.7
            )
            
            # Validate and parse with Pydantic
            try:
                parsed_response = OnboardingResponse.model_validate(response_data)
                conversation_response = parsed_response.response
                is_complete = parsed_response.is_complete
                extracted_data = parsed_response.extracted_data.model_dump(exclude_none=True) if parsed_response.extracted_data else None
            except Exception as e:
                print(f"Warning: Response validation failed: {str(e)}")
                conversation_response = response_data.get("response", "")
                is_complete = response_data.get("is_complete", False)
                extracted_data = response_data.get("extracted_data")
            
            # Save extracted data to database
            if extracted_data:
                try:
                    self._save_extracted_data(extracted_data)
                except Exception as e:
                    print(f"Error saving extracted data: {str(e)}")
            
            return conversation_response, is_complete
        
        except Exception as e:
            print(f"Error in Bedrock invocation: {str(e)}")
            return "I'm having a quick connection hiccup. Ask me again in a moment.", False
    
    def _build_system_prompt(self) -> str:
        """Build system prompt with context about existing user data."""
        prompt = """You are a friendly and helpful fitness assistant helping a user with their health journey.

Your goal is to learn about them through natural, conversational dialogue. Be warm, engaging, and not pushy.

Key information to learn (but don't ask all at once - have a natural conversation):
- Goals: What they want to achieve (weight loss, muscle gain, endurance, flexibility, nutrition, body fat percentage, longevity, etc.)
- Biometrics: Height, weight, age, sex (only if they're comfortable sharing)
- Lifestyle: 
  * Activity level (how active they are)
  * Dietary preferences (vegetarian, vegan, gluten-free, etc.)
  * Workout preferences/constraints (no running, no bike access, prefer weights, etc.)
  * Health conditions (diabetes, injuries, asthma, etc.)
  * Cooking time per day
  * Meal prep preference (daily, weekly, no prep)
  * Budget for food per week

Keep responses brief (2-3 sentences max), friendly, and conversational. If they don't want to share something, that's completely okay - don't push.

IMPORTANT: You have access to an 'additional_context' field in the user profile where you can store any other information you discover that is relevant for helping them reach their goals, even if it doesn't fit into the predefined fields. Examples: "works night shifts", "has food allergies to shellfish", "prefers spicy food", "travels frequently for work", etc. Store this in additional_context as key-value pairs.

After each response, you may have learned new information. You MUST respond with a JSON object following the exact schema provided. Only include fields where you have NEW information. Use null for fields you haven't learned about yet.

For goals:
- If the user mentions a goal that matches an existing goal (similar description or target), update the existing goal rather than creating a duplicate
- If it's a new goal, create it
- Goals can evolve over time - update them if the user provides new information about the same goal

COMPLETION DETECTION:
- Set is_complete to true when you have sufficient information to create a personalized plan
- Minimum requirements: at least one goal, basic biometrics (height/weight or age), and some lifestyle information
- You can ask the user "Is there anything else you'd like to share?" or "Do you feel ready to create your plan?" before marking complete
- If the user says they're done, ready, or indicates they don't want to share more, mark is_complete as true
- If you have enough information even without asking, you can mark it complete"""
        
        # Add context about existing data
        if self.existing_profile:
            existing_info = []
            if self.existing_profile.height_cm:
                existing_info.append(f"Height: {self.existing_profile.height_cm} cm")
            if self.existing_profile.weight_kg:
                existing_info.append(f"Weight: {self.existing_profile.weight_kg} kg")
            if self.existing_profile.age:
                existing_info.append(f"Age: {self.existing_profile.age}")
            if self.existing_profile.dietary_preferences:
                existing_info.append(f"Dietary preferences: {', '.join(self.existing_profile.dietary_preferences)}")
            
            if existing_info:
                prompt += f"\n\nExisting user information: {', '.join(existing_info)}"
        
        if self.existing_goals:
            goals_info = []
            for goal in self.existing_goals:
                goal_info = f"ID: {goal.id}, Type: {goal.goal_type.value}, Description: {goal.description}, Target: {goal.target}"
                if goal.target_value:
                    goal_info += f", Target Value: {goal.target_value}"
                if goal.target_date:
                    goal_info += f", Target Date: {goal.target_date}"
                goals_info.append(goal_info)
            
            prompt += f"\n\nExisting active goals:\n" + "\n".join([f"- {info}" for info in goals_info])
            prompt += "\n\nCRITICAL: When processing goals, you must return the COMPLETE set of goals the user should have after this conversation."
            prompt += "\n- Include ALL existing goals that should remain active (even if unchanged) - use their existing IDs"
            prompt += "\n- If an existing goal should be updated, include it with its ID and the updated fields"
            prompt += "\n- If it's a new goal, omit the ID (it will be created)"
            prompt += "\n- If the user indicates they no longer want a goal, either omit it or set is_active: false"
            prompt += "\n- Use semantic understanding to match goals"
        
        return prompt
    
    def _format_messages(self, conversation_history: List[Message]) -> List[Dict[str, str]]:
        """Format conversation history for Bedrock API."""
        messages = []
        recent_messages = conversation_history[-20:] if len(conversation_history) > 20 else conversation_history
        
        for msg in recent_messages:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return messages
    
    def _get_goal_by_id(self, goal_id: str) -> Optional[Goal]:
        """Get an existing goal by ID."""
        return next((g for g in self.existing_goals if g.id == goal_id), None)
    
    def _save_extracted_data(self, extracted_data: Dict[str, Any]) -> None:
        """Save extracted data to UserProfile and Goal models."""
        if not extracted_data:
            return
        
        # Get or create user profile
        profile = self.existing_profile
        if not profile:
            profile = UserProfile(
                id=str(uuid.uuid4()),
                user_id=self.user_id
            )
            self.db.add(profile)
            self.existing_profile = profile
        
        # Update profile fields if new data is provided
        profile_data = extracted_data.get("profile", {})
        if profile_data:
            for key, value in profile_data.items():
                if value is not None and hasattr(profile, key):
                    if key == "additional_context" and profile.additional_context:
                        if isinstance(profile.additional_context, dict) and isinstance(value, dict):
                            profile.additional_context = {**profile.additional_context, **value}
                        else:
                            profile.additional_context = value
                    elif key in ["dietary_preferences", "workout_preferences", "conditions"]:
                        if isinstance(value, list):
                            existing = getattr(profile, key) or []
                            if isinstance(existing, list):
                                merged = list(set(existing + value))
                                setattr(profile, key, merged)
                            else:
                                setattr(profile, key, value)
                        else:
                            setattr(profile, key, value)
                    else:
                        setattr(profile, key, value)
        
        # Handle goals
        goals_data = extracted_data.get("goals", [])
        if goals_data:
            existing_goal_ids = {g.id for g in self.existing_goals}
            processed_goal_ids = set()
            
            for goal_data in goals_data:
                goal_id = goal_data.get("id")
                is_active = goal_data.get("is_active", True)
                
                if goal_id and goal_id in existing_goal_ids:
                    existing_goal = self._get_goal_by_id(goal_id)
                    if existing_goal:
                        existing_goal.description = goal_data.get("description", existing_goal.description)
                        existing_goal.target = goal_data.get("target", existing_goal.target)
                        if "target_value" in goal_data:
                            existing_goal.target_value = goal_data.get("target_value")
                        if "target_date" in goal_data and goal_data.get("target_date"):
                            try:
                                existing_goal.target_date = date.fromisoformat(goal_data["target_date"])
                            except (ValueError, TypeError):
                                pass
                        if "success_metrics" in goal_data:
                            existing_goal.success_metrics = goal_data.get("success_metrics")
                        existing_goal.is_active = is_active
                        processed_goal_ids.add(goal_id)
                elif not goal_id:
                    try:
                        goal_type = GoalType(goal_data.get("goal_type", "other").lower())
                    except ValueError:
                        goal_type = GoalType.OTHER
                    
                    target_date = None
                    if goal_data.get("target_date"):
                        try:
                            target_date = date.fromisoformat(goal_data["target_date"])
                        except (ValueError, TypeError):
                            pass
                    
                    new_goal = Goal(
                        id=str(uuid.uuid4()),
                        user_id=self.user_id,
                        goal_type=goal_type,
                        description=goal_data.get("description", ""),
                        target=goal_data.get("target", ""),
                        target_value=goal_data.get("target_value"),
                        target_date=target_date,
                        success_metrics=goal_data.get("success_metrics"),
                        is_active=is_active
                    )
                    self.db.add(new_goal)
                    self.existing_goals.append(new_goal)
                    processed_goal_ids.add(new_goal.id)
            
            for existing_goal in self.existing_goals:
                if existing_goal.id not in processed_goal_ids:
                    existing_goal.is_active = False
        
        self.db.commit()
        self.db.refresh(profile)
        self.existing_profile = profile
