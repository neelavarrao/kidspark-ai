from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
import uuid
import asyncio
from datetime import datetime

from app.backend.models.user import User
from app.backend.routers.auth import get_current_user
from app.backend.agents.models.intent import UserMessage, AgentResponse, IntentType
from app.backend.agents.routers.intent_router import IntentRouter
from app.backend.agents.specialized.story_agent import StoryAgent
from app.backend.agents.specialized.activity_agent import ActivityAgent

# Initialize router
router = APIRouter(tags=["Agent"])

# Initialize intent router
intent_router = IntentRouter()

# Story agents are created per-request to maintain separate conversation state
# This dict stores active agents by user ID
story_agents = {}

# Activity agents are created per-request to maintain separate conversation state
activity_agents = {}

@router.post("/intent", response_model=AgentResponse)
async def detect_intent(
    message: UserMessage,
    current_user: User = Depends(get_current_user)
):
    """
    Detect the intent of the user's message without generating a full response.
    This endpoint is useful for testing the intent classification.
    """
    # Add user ID to message if not provided
    if not message.user_id:
        message.user_id = current_user.id

    # Add message ID if not provided
    if not message.message_id:
        message.message_id = str(uuid.uuid4())

    # Detect intent
    intent_result = intent_router.detect_intent(message)
    primary_intent = intent_result.primary_intent

    # Return just the intent classification
    return AgentResponse(
        content=f"Intent detected: {primary_intent.type} (confidence: {primary_intent.confidence:.2f})",
        detected_intent=primary_intent.type,
        metadata={
            "confidence": primary_intent.confidence,
            "detection_method": primary_intent.detection_method,
            "detected_params": primary_intent.detected_params,
            "alternative_intents": [
                {
                    "type": intent.type,
                    "confidence": intent.confidence
                }
                for intent in intent_result.alternative_intents
            ] if intent_result.alternative_intents else []
        }
    )

@router.post("/chat/agent", response_model=AgentResponse)
async def process_agent_message(
    message: UserMessage,
    current_user: User = Depends(get_current_user)
):
    """
    Process a user message through the agent pipeline:
    1. Detect intent
    2. Route to appropriate specialized agent
    3. Return response
    """
    # Add user ID to message if not provided
    if not message.user_id:
        message.user_id = current_user.id

    # Add message ID if not provided
    if not message.message_id:
        message.message_id = str(uuid.uuid4())

    # Add timestamp if not provided
    if not message.timestamp:
        message.timestamp = datetime.utcnow()

    # Detect intent
    intent_result = intent_router.detect_intent(message)
    primary_intent = intent_result.primary_intent

    # Route to appropriate specialized agent based on intent
    try:
        if primary_intent.type == IntentType.STORY:
            # Get or create a StoryAgent for this user
            user_id = str(message.user_id) if message.user_id else str(uuid.uuid4())
            if user_id not in story_agents:
                story_agents[user_id] = StoryAgent(
                    run_id=str(uuid.uuid4()),
                    user_id=user_id
                )

            # Extract child age from detected params if available
            detected_params = primary_intent.detected_params or {}

            # Use handle_message to go through the LangChain agent with middleware
            # This ensures guardrails (toxicity, on-topic) are applied
            story_result = await story_agents[user_id].handle_message(message.content)

            if story_result.get("success") and story_result.get("story_data"):
                # Return response with story data for the modal
                return AgentResponse(
                    content=story_result["message"],
                    detected_intent=primary_intent.type,
                    metadata={
                        "confidence": primary_intent.confidence,
                        "detection_method": primary_intent.detection_method,
                        "detected_params": detected_params,
                        "display_type": "story",
                        "story_data": story_result["story_data"]
                    }
                )
            else:
                # No story found or guardrail blocked, return the message
                return AgentResponse(
                    content=story_result.get("message", "I couldn't find a story. Please try again."),
                    detected_intent=primary_intent.type,
                    metadata={
                        "confidence": primary_intent.confidence,
                        "detection_method": primary_intent.detection_method,
                        "detected_params": detected_params
                    }
                )
        elif primary_intent.type == IntentType.ACTIVITY:
            # Get or create an ActivityAgent for this user
            user_id = str(message.user_id) if message.user_id else str(uuid.uuid4())
            if user_id not in activity_agents:
                activity_agents[user_id] = ActivityAgent(
                    run_id=str(uuid.uuid4()),
                    user_id=user_id
                )

            # Extract parameters from detected params
            detected_params = primary_intent.detected_params or {}

            # Use handle_message to go through the LangChain agent with middleware
            # This ensures guardrails (toxicity, on-topic) are applied
            activity_result = await activity_agents[user_id].handle_message(message.content)

            if activity_result.get("success") and activity_result.get("activity_data"):
                # Return response with activity data for the modal
                return AgentResponse(
                    content=activity_result["message"],
                    detected_intent=primary_intent.type,
                    metadata={
                        "confidence": primary_intent.confidence,
                        "detection_method": primary_intent.detection_method,
                        "detected_params": detected_params,
                        "display_type": "activity",
                        "activity_data": activity_result["activity_data"]
                    }
                )
            else:
                # No activity found or guardrail blocked, return the message
                return AgentResponse(
                    content=activity_result.get("message", "I couldn't find an activity. Please try again."),
                    detected_intent=primary_intent.type,
                    metadata={
                        "confidence": primary_intent.confidence,
                        "detection_method": primary_intent.detection_method,
                        "detected_params": detected_params
                    }
                )
        elif primary_intent.type == IntentType.WHY:
            # Placeholder for explanation agent (future implementation)
            response_content = "That's a great question! In the next phase, I'll have child-friendly explanations."
        elif primary_intent.type == IntentType.GREETING:
            response_content = "Hello! I'm KidSpark AI, your parenting assistant. How can I help you today?"
        else:
            response_content = "I'm not quite sure what you're looking for. Would you like an activity suggestion, a bedtime story, or an answer to a question?"

        # For intents without specialized agents yet, return a simple response
        return AgentResponse(
            content=response_content,
            detected_intent=primary_intent.type,
            metadata={
                "confidence": primary_intent.confidence,
                "detection_method": primary_intent.detection_method,
                "detected_params": primary_intent.detected_params
            }
        )

    except Exception as e:
        # Handle any errors from specialized agents
        error_message = f"I'm sorry, I encountered an issue processing your request. Please try again."
        return AgentResponse(
            content=error_message,
            detected_intent=primary_intent.type,
            metadata={
                "error": str(e),
                "confidence": primary_intent.confidence
            }
        )