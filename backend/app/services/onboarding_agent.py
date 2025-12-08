"""Onboarding agent for conversational data collection."""
from sqlalchemy.orm import Session
from typing import List
from app.models.message import Message


class OnboardingAgent:
    """Agent for handling onboarding conversations."""
    
    def __init__(self, db: Session):
        self.db = db
        self.system_prompt = """You are a friendly and helpful fitness assistant helping a new user get started.
Your goal is to learn about them through natural conversation. Be conversational, not pushy.
Ask about their goals, biometrics (height, weight, age, sex), and lifestyle constraints (cooking time, meal prep preferences, budget, dietary preferences, activity level).
Don't ask all questions at once - have a natural conversation. If they don't want to share something, that's okay.
Keep responses brief and friendly."""
    
    async def get_response(
        self,
        user_message: str,
        conversation_history: List[Message]
    ) -> str:
        """
        Generate a response based on user message and conversation history.
        
        For now, returns a simple echo response. Will be replaced with AI integration.
        """
        # TODO: Integrate with AI service (OpenAI, Bedrock, etc.)
        # For now, return a simple response
        if not conversation_history or len(conversation_history) == 1:
            return "Hi! I'm here to help you create a personalized fitness and nutrition plan. Let's start by getting to know you a bit. What are your main fitness or health goals?"
        
        # Simple echo for testing
        return f"I understand you said: '{user_message}'. Can you tell me more about that?"

