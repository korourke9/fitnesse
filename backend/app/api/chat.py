"""Chat API endpoint with internal agent routing."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from app.core.database import get_db
from app.models.user import User
from app.models.conversation import Conversation, AgentType
from app.models.message import Message
from app.api.schemas.chat import ChatRequest, ChatResponse, MessageResponse
from app.services.onboarding import OnboardingAgent
from app.services.coordination import CoordinationAgent
from app.services.plan_generation import MealPlanGenerator, WorkoutPlanGenerator

router = APIRouter(prefix="/api", tags=["chat"])


def get_or_create_user(db: Session) -> User:
    """Get or create the current user. TODO: Replace with auth."""
    temp_user_id = "temp-user-123"
    temp_user_email = "temp@fitnesse.local"
    
    user = db.query(User).filter(User.id == temp_user_id).first()
    if not user:
        user = User(id=temp_user_id, email=temp_user_email)
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user


def get_or_create_conversation(db: Session, user_id: str, conversation_id: str = None) -> Conversation:
    """Get existing conversation or create a new one."""
    if conversation_id:
        conversation = db.query(Conversation).filter(
            Conversation.id == conversation_id
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation
    
    # Create new conversation - starts with onboarding
    conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        agent_type=AgentType.ONBOARDING
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


async def handle_onboarding(
    db: Session,
    user_id: str,
    conversation: Conversation,
    user_message_content: str,
    messages: list
) -> tuple[str, dict]:
    """Handle onboarding agent interactions."""
    agent = OnboardingAgent(db=db, user_id=user_id)
    response_content, is_complete = await agent.get_response(
        user_message=user_message_content,
        conversation_history=messages
    )
    
    metadata = {"agent_type": AgentType.ONBOARDING.value}
    
    # If onboarding is complete, transition to coordination
    if is_complete:
        metadata["is_complete"] = True
        
        # Transition to coordination agent
        conversation.agent_type = AgentType.COORDINATION
        db.commit()
        
        # Replace with coordination greeting (onboarding message becomes redundant)
        coord_response, coord_metadata = await handle_coordination(
            db, user_id, conversation, user_message_content, messages, is_initial_greeting=True
        )
        response_content = coord_response  # Replace, not append
        metadata = {**metadata, **coord_metadata}
    
    return response_content, metadata


async def handle_coordination(
    db: Session,
    user_id: str,
    conversation: Conversation,
    user_message_content: str,
    messages: list,
    is_initial_greeting: bool = False
) -> tuple[str, dict]:
    """Handle coordination agent interactions.
    
    When routing to another agent, immediately calls that agent
    so the user gets a response without sending another message.
    """
    metadata = {"agent_type": AgentType.COORDINATION.value}
    
    # If this is an initial greeting (e.g., after onboarding), return a welcome message
    if is_initial_greeting:
        response_content = "🎉 Great! I have everything I need to create your personalized plans. What would you like to do first?\n• Generate your meal plan\n• Generate your workout plan"
        return response_content, metadata
    
    agent = CoordinationAgent(db=db, user_id=user_id)
    response_content, suggested_agent, action = await agent.get_response(
        user_message=user_message_content,
        conversation_history=messages
    )
    
    metadata = {
        "agent_type": AgentType.COORDINATION.value,
        "suggested_agent": suggested_agent,
        "action": action
    }
    
    # Handle meal plan generation - then route to nutritionist
    if action == "generate_meal_plan":
        try:
            meal_generator = MealPlanGenerator(db=db, user_id=user_id)
            plan = await meal_generator.generate(duration_days=30)
            metadata["plan_id"] = plan.id
            metadata["meal_plan_generated"] = True
            
            # Route to nutritionist after generating meal plan
            conversation.agent_type = AgentType.NUTRITIONIST
            db.commit()
            
            response_content = "🍽️ Your personalized meal plan is ready!\n\nI've created a nutrition plan tailored to your goals. Now let me connect you with our nutritionist who can help you track your meals and stay on target."
            
            # Get nutritionist greeting
            nutritionist_response, nutritionist_metadata = await handle_nutritionist(
                db, user_id, conversation, user_message_content, messages, is_initial_greeting=True
            )
            response_content += f"\n\n{nutritionist_response}"
            metadata = {**metadata, **nutritionist_metadata}
            
        except Exception as e:
            print(f"Error generating meal plan: {str(e)}")
            response_content += "\n\nI had trouble generating your meal plan. Let's try again - just ask me to create your meal plan."
    
    # Handle workout plan generation - then route to trainer
    elif action == "generate_workout_plan":
        try:
            workout_generator = WorkoutPlanGenerator(db=db, user_id=user_id)
            plan = await workout_generator.generate(duration_days=30)
            metadata["plan_id"] = plan.id
            metadata["workout_plan_generated"] = True
            
            # Route to trainer after generating workout plan
            conversation.agent_type = AgentType.TRAINER
            db.commit()
            
            response_content = "💪 Your personalized workout plan is ready!\n\nI've created an exercise plan tailored to your goals. Now let me connect you with our trainer who can help you track your workouts and stay on target."
            
            # Get trainer greeting
            trainer_response, trainer_metadata = await handle_trainer(
                db, user_id, conversation, user_message_content, messages, is_initial_greeting=True
            )
            response_content += f"\n\n{trainer_response}"
            metadata = {**metadata, **trainer_metadata}
            
        except Exception as e:
            print(f"Error generating workout plan: {str(e)}")
            response_content += "\n\nI had trouble generating your workout plan. Let's try again - just ask me to create your workout plan."
    
    # Handle routing to other agents - immediately call the new agent
    elif action == "route_to_nutritionist":
        conversation.agent_type = AgentType.NUTRITIONIST
        db.commit()
        # Immediately get response from nutritionist with initial greeting
        nutritionist_response, nutritionist_metadata = await handle_nutritionist(
            db, user_id, conversation, user_message_content, messages, is_initial_greeting=True
        )
        response_content = nutritionist_response
        metadata = nutritionist_metadata
        
    elif action == "route_to_trainer":
        conversation.agent_type = AgentType.TRAINER
        db.commit()
        # Immediately get response from trainer with initial greeting
        trainer_response, trainer_metadata = await handle_trainer(
            db, user_id, conversation, user_message_content, messages, is_initial_greeting=True
        )
        response_content = trainer_response
        metadata = trainer_metadata
    
    # Keep action in metadata for frontend reference
    if action:
        metadata["action"] = action
    
    return response_content, metadata


async def handle_nutritionist(
    db: Session,
    user_id: str,
    conversation: Conversation,
    user_message_content: str,
    messages: list,
    is_initial_greeting: bool = False
) -> tuple[str, dict]:
    """Handle nutritionist agent interactions. TODO: Implement full nutritionist agent."""
    metadata = {"agent_type": AgentType.NUTRITIONIST.value}
    
    # Check if user wants to switch agents
    lower_msg = user_message_content.lower()
    if any(phrase in lower_msg for phrase in ["switch to trainer", "talk to trainer", "log workout", "log exercise"]):
        conversation.agent_type = AgentType.TRAINER
        db.commit()
        # Immediately get response from trainer
        trainer_response, trainer_metadata = await handle_trainer(
            db, user_id, conversation, user_message_content, messages, is_initial_greeting=True
        )
        return f"💪 Switching you to our trainer...\n\n{trainer_response}", trainer_metadata
    
    if any(phrase in lower_msg for phrase in ["go back", "main menu", "what can i do", "help"]):
        conversation.agent_type = AgentType.COORDINATION
        db.commit()
        metadata["agent_type"] = AgentType.COORDINATION.value
        return "Sure! I'm here to help you navigate. Would you like to:\n• Log meals with our nutritionist\n• Log workouts with our trainer\n• View your plan\n• Generate your workout plan", metadata
    
    # Check if this is just a routing message (user asked to talk to nutritionist)
    if is_initial_greeting or any(phrase in lower_msg for phrase in ["log meal", "log food", "talk to nutritionist", "nutrition"]):
        response_content = "Hi! I'm your nutritionist. I'll help you track your meals and nutrition. 🥗\n\nWhat did you eat? You can describe your meal naturally, like:\n• \"I had eggs and toast for breakfast\"\n• \"Chicken salad with avocado for lunch\"\n• \"A protein shake after my workout\""
        return response_content, metadata
    
    # TODO: Implement full nutritionist agent with Bedrock
    # For now, provide a helpful placeholder response
    response_content = f"🥗 Got it! I've logged: \"{user_message_content}\"\n\n(Full calorie/macro tracking coming soon!)\n\nWhat else did you eat, or say \"help\" for options."
    
    return response_content, metadata


async def handle_trainer(
    db: Session,
    user_id: str,
    conversation: Conversation,
    user_message_content: str,
    messages: list,
    is_initial_greeting: bool = False
) -> tuple[str, dict]:
    """Handle trainer agent interactions. TODO: Implement full trainer agent."""
    metadata = {"agent_type": AgentType.TRAINER.value}
    
    # Check if user wants to switch agents
    lower_msg = user_message_content.lower()
    if any(phrase in lower_msg for phrase in ["switch to nutritionist", "talk to nutritionist", "log meal", "log food"]):
        conversation.agent_type = AgentType.NUTRITIONIST
        db.commit()
        # Immediately get response from nutritionist
        nutritionist_response, nutritionist_metadata = await handle_nutritionist(
            db, user_id, conversation, user_message_content, messages, is_initial_greeting=True
        )
        return f"🥗 Switching you to our nutritionist...\n\n{nutritionist_response}", nutritionist_metadata
    
    if any(phrase in lower_msg for phrase in ["go back", "main menu", "what can i do", "help"]):
        conversation.agent_type = AgentType.COORDINATION
        db.commit()
        metadata["agent_type"] = AgentType.COORDINATION.value
        return "Sure! I'm here to help you navigate. Would you like to:\n• Log meals with our nutritionist\n• Log workouts with our trainer\n• View your plan\n• Generate your workout plan", metadata
    
    # Check if this is just a routing message (user asked to talk to trainer)
    if is_initial_greeting or any(phrase in lower_msg for phrase in ["log workout", "log exercise", "talk to trainer", "workout", "exercise"]):
        response_content = "Hey! I'm your personal trainer. Let's track your workouts! 💪\n\nWhat did you do today? Describe your workout naturally, like:\n• \"30 minutes on the treadmill\"\n• \"Chest and back day - bench press, rows, pullups\"\n• \"Yoga for 45 minutes\"\n• \"10,000 steps today\""
        return response_content, metadata
    
    # TODO: Implement full trainer agent with Bedrock
    # For now, provide a helpful placeholder response
    response_content = f"💪 Nice work! I've logged: \"{user_message_content}\"\n\n(Full exercise tracking coming soon!)\n\nWhat else did you do, or say \"help\" for options."
    
    return response_content, metadata


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
    # Get or create user
    user = get_or_create_user(db)
    
    # Get or create conversation
    conversation = get_or_create_conversation(db, user.id, request.conversation_id)
    
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
    
    # Route to appropriate agent based on conversation state
    agent_type = conversation.agent_type
    
    if agent_type == AgentType.ONBOARDING:
        response_content, metadata = await handle_onboarding(
            db, user.id, conversation, request.message, messages
        )
    elif agent_type == AgentType.COORDINATION:
        response_content, metadata = await handle_coordination(
            db, user.id, conversation, request.message, messages
        )
    elif agent_type == AgentType.NUTRITIONIST:
        response_content, metadata = await handle_nutritionist(
            db, user.id, conversation, request.message, messages
        )
    elif agent_type == AgentType.TRAINER:
        response_content, metadata = await handle_trainer(
            db, user.id, conversation, request.message, messages
        )
    else:
        # Fallback to coordination
        response_content, metadata = await handle_coordination(
            db, user.id, conversation, request.message, messages
        )
    
    # Save assistant message
    assistant_message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation.id,
        role="assistant",
        content=response_content
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
        ),
        metadata=metadata
    )
