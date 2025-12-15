from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from typing import List, Dict, Optional
from datetime import datetime
import json
import uuid
import logging

from app.backend.models.user import User, ChatMessage
from app.backend.routers.auth import get_current_user
from app.backend.services.supabase_service import get_supabase_client
from app.backend.agents.routers.intent_router import IntentRouter
from app.backend.agents.models.intent import IntentType, UserMessage
from app.backend.agents.specialized.story_agent import StoryAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

router = APIRouter(tags=["Chat"])

# In-memory store of active connections (in a production app, use Redis)
active_connections: Dict[str, WebSocket] = {}

# Store StoryAgent instances per client for conversation continuity
story_agents: Dict[str, StoryAgent] = {}

# Initialize the intent router (singleton)
intent_router = IntentRouter()


async def process_message(content: str, client_id: str) -> str:
    """
    Process a user message through intent detection and route to appropriate agent.

    Args:
        content: The user's message content
        client_id: The client/user ID

    Returns:
        The response from the appropriate agent
    """
    try:
        # Detect intent
        user_message = UserMessage(
            content=content,
            user_id=client_id,
            message_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow()
        )

        intent_result = intent_router.detect_intent(user_message)
        intent_type = intent_result.primary_intent.type

        logger.info(f"Detected intent: {intent_type} with confidence {intent_result.primary_intent.confidence}")

        # Route to appropriate agent based on intent
        if intent_type == IntentType.STORY:
            # Get or create StoryAgent for this client
            if client_id not in story_agents:
                story_agents[client_id] = StoryAgent(
                    run_id=str(uuid.uuid4()),
                    user_id=client_id
                )

            agent = story_agents[client_id]
            response = await agent.handle_message(content)
            return response

        elif intent_type == IntentType.GREETING:
            return "Hello! I'm KidSpark AI, your friendly parenting assistant. I can help you with:\n\n" \
                   "- **Bedtime stories** - Just ask for a story about any theme!\n" \
                   "- **Activity suggestions** - Coming soon!\n" \
                   "- **Answering 'why' questions** - Coming soon!\n\n" \
                   "What would you like today?"

        elif intent_type == IntentType.ACTIVITY:
            return "I'd love to suggest some activities for your child! This feature is coming soon. " \
                   "In the meantime, would you like me to tell you a bedtime story instead?"

        elif intent_type == IntentType.WHY:
            return "That's a great question! The 'why' question answering feature is coming soon. " \
                   "For now, I can help you with bedtime stories. Would you like to hear one?"

        else:
            # Unknown intent - provide helpful response
            return "I'm not quite sure what you're looking for. I can help with:\n\n" \
                   "- **Bedtime stories** - Ask me for a story about adventure, princesses, dinosaurs, or any theme!\n" \
                   "- **Activity suggestions** - Coming soon!\n" \
                   "- **Answering questions** - Coming soon!\n\n" \
                   "What would you like to try?"

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return f"I'm sorry, something went wrong while processing your request. Please try again. Error: {str(e)}"


@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for real-time chat with KidSpark AI.
    Routes messages to appropriate agents based on detected intent.
    """
    await websocket.accept()
    active_connections[client_id] = websocket

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            content = message.get("content", "")

            logger.info(f"Received message from {client_id}: {content[:50]}...")

            # Process the message through intent detection and agent routing
            response_content = await process_message(content, client_id)

            # Prepare response
            response = {
                "id": str(uuid.uuid4()),
                "content": response_content,
                "sender": "assistant",
                "timestamp": datetime.utcnow().isoformat()
            }

            # Store message in Supabase
            try:
                supabase = get_supabase_client()
                # Store user message
                supabase.table("chat_messages").insert({
                    "user_id": client_id,
                    "content": content,
                    "sender": "user",
                    "timestamp": message.get("timestamp", datetime.utcnow().isoformat())
                }).execute()

                # Store assistant response
                supabase.table("chat_messages").insert({
                    "user_id": client_id,
                    "content": response_content,
                    "sender": "assistant",
                    "timestamp": response["timestamp"]
                }).execute()
            except Exception as e:
                logger.error(f"Error storing chat messages: {str(e)}")
                # Continue even if storage fails

            # Send response back to client
            await websocket.send_text(json.dumps(response))

    except WebSocketDisconnect:
        if client_id in active_connections:
            del active_connections[client_id]
        # Clean up story agent for this client
        if client_id in story_agents:
            del story_agents[client_id]
        logger.info(f"Client {client_id} disconnected")


@router.post("/messages", response_model=ChatMessage)
async def create_message(message: ChatMessage, current_user: User = Depends(get_current_user)):
    """
    REST API alternative to WebSockets for simple chat functionality.
    This endpoint allows sending messages via regular HTTP requests.
    Routes messages to appropriate agents based on detected intent.
    """
    # Set timestamp if not provided
    if not message.timestamp:
        message.timestamp = datetime.utcnow()

    # Use user ID from authenticated user
    client_id = str(current_user.id) if hasattr(current_user, 'id') else str(uuid.uuid4())

    # Process the message through intent detection and agent routing
    response_content = await process_message(message.content, client_id)

    response = ChatMessage(
        content=response_content,
        sender="assistant",
        timestamp=datetime.utcnow()
    )

    return response


@router.get("/messages/history", response_model=List[ChatMessage])
async def get_message_history(current_user: User = Depends(get_current_user)):
    """
    Get chat message history for the current user.
    Fetches from Supabase.
    """
    try:
        supabase = get_supabase_client()
        user_id = str(current_user.id) if hasattr(current_user, 'id') else None

        if not user_id:
            return []

        # Fetch chat history from Supabase
        response = supabase.table("chat_messages") \
            .select("content, sender, timestamp") \
            .eq("user_id", user_id) \
            .order("timestamp", desc=False) \
            .limit(50) \
            .execute()

        if response.data:
            return [
                ChatMessage(
                    content=msg["content"],
                    sender=msg["sender"],
                    timestamp=datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00"))
                    if isinstance(msg["timestamp"], str)
                    else msg["timestamp"]
                )
                for msg in response.data
            ]

        return []

    except Exception as e:
        logger.error(f"Error fetching message history: {str(e)}")
        # Return welcome message on error
        return [
            ChatMessage(
                content="Hello! How can I help you with parenting today?",
                sender="assistant",
                timestamp=datetime.utcnow()
            ),
        ]
