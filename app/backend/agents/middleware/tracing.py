from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain_core.messages import ToolMessage, AIMessage, HumanMessage
from langgraph.runtime import Runtime
import os
from supabase import Client
import logging
import json
import uuid

from app.backend.services.supabase_service import get_supabase_client

# Configure logging for tracing
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TracingMiddleware(AgentMiddleware):
    """Middleware to trace agent operations and store them in Supabase"""

    def __init__(self, run_id: str = None,
                 agent_id: str = None,
                 user_id: str = None,
                 max_messages: int = 50):
        super().__init__()
        self.run_id = run_id or str(uuid.uuid4())
        self.agent_id = agent_id or 'intent_router'
        self.user_id = user_id
        self.max_messages = max_messages
        self.supabase = get_supabase_client()

    def _ensure_traces_table(self):
        """Ensure the traces table exists in Supabase"""
        # This could be done during app initialization or in a migration script
        # For now we'll just log if there's an issue
        try:
            # Check if table exists by trying to select from it
            self.supabase.table("agent_traces").select("run_id").limit(1).execute()
            logger.info("agent_traces table exists")
        except Exception as e:
            logger.error(f"Error checking agent_traces table: {str(e)}. Please create it manually.")

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, any] | None:
        """Log agent responses after processing"""
        logger.info(f'[TracingMiddleware] after_agent for run_id: {self.run_id}')
        self.log_trace(state.get('messages', []))
        return None

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, any] | None:
        """Check message limit and log current state before model processing"""
        if len(state["messages"]) >= self.max_messages:
            return {
                "messages": [AIMessage(content="Conversation limit reached.")],
                "jump_to": "end"
            }

        logger.info(f'[TracingMiddleware] before_model for run_id: {self.run_id}')
        self.log_trace(state.get('messages', []))
        return None

    def log_trace(self, messages):
        """Log agent traces to Supabase and console"""
        for message in messages:
            # Determine message type
            message_type = ''
            if isinstance(message, HumanMessage):
                message_type = 'human'
            elif isinstance(message, AIMessage):
                message_type = 'ai'
            elif isinstance(message, ToolMessage):
                message_type = 'tool'
            else:
                message_type = 'unknown'

            # Extract failure mode if present
            failure_mode = message.additional_kwargs.get('failure_mode') if hasattr(message, 'additional_kwargs') else None

            # Extract tool call information for AI messages
            tool_info_list = []
            if isinstance(message, AIMessage) and hasattr(message, 'tool_calls') and message.tool_calls:
                for tool_call in message.tool_calls:
                    tool_info = {
                        'tool': tool_call.get('name', 'unknown'),
                        'args': tool_call.get('args', {})
                    }
                    tool_info_list.append(tool_info)
                    logger.info(f"[RUN_ID: {self.run_id}] 🔧 Tool Called: {tool_info['tool']}")
                    logger.info(f"[RUN_ID: {self.run_id}]    Arguments: {tool_info['args']}")

            # Log tool message details
            if isinstance(message, ToolMessage):
                logger.info(f"[RUN_ID: {self.run_id}] 🔧 Tool Called: {message.name if hasattr(message, 'name') else 'unknown'}")
                logger.info(f"[RUN_ID: {self.run_id}]    Content: {message.content}")

            # Extract content safely
            content = message.content if hasattr(message, 'content') else str(message)

            # Store trace in Supabase
            try:
                trace_data = {
                    'run_id': self.run_id,
                    'agent_id': self.agent_id,
                    'user_id': self.user_id,
                    'message_type': message_type,
                    'failure_mode': failure_mode,
                    'tool_call_info': json.dumps(tool_info_list) if tool_info_list else None,
                    'content': content
                }

                self.supabase.table("agent_traces").insert(trace_data).execute()
            except Exception as e:
                logger.error(f"Error logging trace to Supabase: {str(e)}")
                # Continue execution even if logging fails