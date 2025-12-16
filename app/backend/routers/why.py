"""
Why Router for KidSpark AI
Handles API endpoints for the "Ask Me Why" feature.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pydantic import BaseModel
from typing import Optional
import uuid

from app.backend.models.user import User
from app.backend.routers.auth import get_current_user
from app.backend.agents.specialized.why_agent import WhyAgent

# Initialize router
router = APIRouter(tags=["Why"])

# Templates
templates = Jinja2Templates(directory="app/frontend/templates")

# Store active Why agents by session ID
why_agents = {}


class WhyQuestion(BaseModel):
    """Request model for a why question."""
    question: str
    age_group: str = "5-6"  # "3-4", "5-6", or "7+"
    is_follow_up: bool = False
    session_id: Optional[str] = None


class WhyResponse(BaseModel):
    """Response model for a why answer."""
    success: bool
    answer: str
    question: Optional[str] = None
    can_follow_up: bool = True
    session_id: str


@router.get("/why", response_class=HTMLResponse)
async def why_page(request: Request):
    """Serve the Ask Me Why page."""
    return templates.TemplateResponse("why.html", {"request": request})


@router.post("/api/why", response_model=WhyResponse)
async def ask_why(
    question_data: WhyQuestion,
    current_user: User = Depends(get_current_user)
):
    """
    Answer a "why" question with a child-friendly explanation.

    Args:
        question_data: The question and settings
        current_user: The authenticated user

    Returns:
        WhyResponse with the answer
    """
    # Get or create session ID
    session_id = question_data.session_id or str(uuid.uuid4())

    # Create a unique key combining user and session
    agent_key = f"{current_user.id}:{session_id}"

    # Get or create WhyAgent for this session
    if agent_key not in why_agents:
        why_agents[agent_key] = WhyAgent(
            run_id=session_id,
            user_id=str(current_user.id)
        )

    agent = why_agents[agent_key]

    # Get the answer
    result = await agent.answer_question(
        question=question_data.question,
        age_group=question_data.age_group,
        is_follow_up=question_data.is_follow_up
    )

    return WhyResponse(
        success=result["success"],
        answer=result["answer"],
        question=result.get("question"),
        can_follow_up=result.get("can_follow_up", True),
        session_id=session_id
    )


@router.post("/api/why/clear")
async def clear_why_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Clear a why session's conversation history.

    Args:
        session_id: The session to clear
        current_user: The authenticated user

    Returns:
        Success status
    """
    agent_key = f"{current_user.id}:{session_id}"

    if agent_key in why_agents:
        why_agents[agent_key].clear_history()
        return {"success": True, "message": "Session cleared"}

    return {"success": True, "message": "No session found"}
