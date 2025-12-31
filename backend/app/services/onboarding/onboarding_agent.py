"""Onboarding agent for conversational data collection."""
import json
import uuid
from typing import List, Dict, Any, Optional
from datetime import date
from sqlalchemy.orm import Session

from app.models.message import Message
from app.models.user_profile import UserProfile
from app.models.goal import Goal, GoalType
from app.services.bedrock import BedrockService
from app.services.onboarding.onboarding_schema import OnboardingResponse
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
- Goals can evolve over time - update them if the user provides new information about the same goal"""
        
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
            prompt += "\n- Use semantic understanding to match goals: 'lose weight' and 'get to 180 lbs' are likely the same goal if the user weighs more than 180"
            prompt += "\n- If the user changes their mind about a goal (e.g., 'actually I want to gain muscle instead'), update the existing goal rather than creating a new one"
        
        return prompt
    
    def _format_messages(self, conversation_history: List[Message]) -> List[Dict[str, str]]:
        """Format conversation history for Bedrock API."""
        messages = []
        
        # Keep recent messages (last 10 turns = 20 messages)
        # For longer conversations, we could summarize older ones
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
                    # For additional_context, merge with existing if present
                    if key == "additional_context" and profile.additional_context:
                        if isinstance(profile.additional_context, dict) and isinstance(value, dict):
                            profile.additional_context = {**profile.additional_context, **value}
                        else:
                            profile.additional_context = value
                    # For arrays (dietary_preferences, workout_preferences, conditions), merge unique values
                    elif key in ["dietary_preferences", "workout_preferences", "conditions"]:
                        if isinstance(value, list):
                            existing = getattr(profile, key) or []
                            if isinstance(existing, list):
                                # Merge and deduplicate
                                merged = list(set(existing + value))
                                setattr(profile, key, merged)
                            else:
                                setattr(profile, key, value)
                        else:
                            setattr(profile, key, value)
                    else:
                        setattr(profile, key, value)
        
        # Handle goals - model returns complete goal state
        goals_data = extracted_data.get("goals", [])
        if goals_data:
            # Get all existing goal IDs for reference
            existing_goal_ids = {g.id for g in self.existing_goals}
            processed_goal_ids = set()
            
            for goal_data in goals_data:
                goal_id = goal_data.get("id")
                is_active = goal_data.get("is_active", True)
                
                if goal_id and goal_id in existing_goal_ids:
                    # Update existing goal
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
                    # Create new goal
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
                    # Add to existing_goals list for future reference
                    self.existing_goals.append(new_goal)
                    processed_goal_ids.add(new_goal.id)
            
            # Deactivate any existing goals that weren't included in the response
            # (model decided they should be removed)
            for existing_goal in self.existing_goals:
                if existing_goal.id not in processed_goal_ids:
                    existing_goal.is_active = False
        
        self.db.commit()
        # Refresh existing_profile in case it was just created
        self.db.refresh(profile)
        self.existing_profile = profile
    
    async def get_response(
        self,
        user_message: str,
        conversation_history: List[Message]
    ) -> str:
        """
        Generate a response based on user message and conversation history.
        
        Uses AWS Bedrock to generate conversational responses and extract
        structured data from the conversation.
        """
        # Format messages for Bedrock
        messages = self._format_messages(conversation_history)
        
        try:
            # Use structured output for reliable data extraction
            # This ensures we get both the conversational response and extracted data in one call
            response_data = self.bedrock.invoke_structured(
                messages=messages,
                output_schema=self.response_schema,
                system_prompt=self.system_prompt,
                max_tokens=2048,
                temperature=0.7
            )
            
            # Validate and parse with Pydantic for type safety
            try:
                parsed_response = OnboardingResponse.model_validate(response_data)
                conversation_response = parsed_response.response
                # Convert Pydantic model to dict for saving
                extracted_data = parsed_response.extracted_data.model_dump(exclude_none=True) if parsed_response.extracted_data else None
            except Exception as e:
                # If validation fails, try to extract what we can (fallback)
                print(f"Warning: Response validation failed: {str(e)}")
                conversation_response = response_data.get("response", "")
                extracted_data = response_data.get("extracted_data")
            
            # Save extracted data to database
            if extracted_data:
                try:
                    self._save_extracted_data(extracted_data)
                except Exception as e:
                    # Log error but don't fail the response
                    print(f"Error saving extracted data: {str(e)}")
            
            return conversation_response
        
        except Exception as e:
            # Fallback response on error
            print(f"Error in Bedrock invocation: {str(e)}")
            return "I'm having a bit of trouble right now. Could you try rephrasing that? I'm here to help you create a personalized fitness and nutrition plan!"

