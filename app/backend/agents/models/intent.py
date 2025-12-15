from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class IntentType(str, Enum):
    """Types of intents that KidSpark AI can handle"""
    ACTIVITY = "activity"  # Activity suggestions
    STORY = "story"        # Bedtime stories
    WHY = "why"            # Explanations to curious questions
    UNKNOWN = "unknown"    # Fallback for unclear intents
    GREETING = "greeting"  # Simple greetings

class Intent(BaseModel):
    """
    Represents a detected user intent
    """
    type: IntentType
    confidence: float
    detected_params: Optional[Dict[str, Any]] = None
    raw_input: str
    detection_method: str = "regex"  # "regex" or "llm"
    timestamp: Optional[datetime] = None

class IntentDetectionResult(BaseModel):
    """
    Result of intent detection with possibly multiple intents
    """
    primary_intent: Intent
    alternative_intents: Optional[List[Intent]] = None
    user_id: Optional[str] = None
    message_id: Optional[str] = None

class UserMessage(BaseModel):
    """
    Message from the user to be processed
    """
    content: str
    user_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    message_id: Optional[str] = None

class AgentResponse(BaseModel):
    """
    Response from the agent to the user
    """
    content: str
    detected_intent: Optional[IntentType] = None
    metadata: Optional[Dict[str, Any]] = None