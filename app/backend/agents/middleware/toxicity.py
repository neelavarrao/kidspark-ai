from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime
from openai import OpenAI
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ToxicityDetectionMiddleware(AgentMiddleware):
    """
    Middleware to detect toxic, harmful, or inappropriate content in messages
    using OpenAI's moderation API. Important for a child-focused application.

    Detects:
    - Hate speech
    - Harassment
    - Self-harm content
    - Sexual content
    - Violence
    - Other harmful content categories
    """

    def __init__(self,
                 block_toxic_input: bool = True,
                 sanitize_toxic_output: bool = True,
                 log_detections: bool = True,
                 toxicity_threshold: float = 0.5):
        """
        Args:
            block_toxic_input: If True, prevent processing when toxic input is detected
            sanitize_toxic_output: If True, sanitize toxic content in agent responses
            log_detections: If True, log all toxicity detections
            toxicity_threshold: Threshold for flagging content (0.0-1.0)
        """
        super().__init__()
        self.block_toxic_input = block_toxic_input
        self.sanitize_toxic_output = sanitize_toxic_output
        self.log_detections = log_detections
        self.toxicity_threshold = toxicity_threshold
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def check_toxicity(self, text: str) -> dict:
        """
        Check text for toxicity using OpenAI's moderation API

        Returns:
            dict with 'flagged' (bool) and 'categories' (dict) keys
        """
        if not isinstance(text, str) or not text.strip():
            return {"flagged": False, "categories": {}}

        try:
            response = self.openai_client.moderations.create(input=text)
            result = response.results[0]

            # Check if any category is flagged according to our threshold
            flagged = False
            categories = {}

            for category, score in result.category_scores.model_dump().items():
                if score >= self.toxicity_threshold:
                    flagged = True
                    categories[category] = score

            return {
                "flagged": flagged,
                "categories": categories
            }

        except Exception as e:
            logger.error(f"Error checking toxicity: {str(e)}")
            return {"flagged": False, "categories": {}}

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, any] | None:
        """Check for toxicity in user input before agent processing"""
        # Find the last human message
        messages = state.get('messages', [])
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]

        if not human_messages:
            return None

        last_human_message = human_messages[-1]
        content = last_human_message.content

        # Check for toxicity
        toxicity_result = self.check_toxicity(content)
        logger.info(f"Toxicity check result: {toxicity_result}")
        if toxicity_result["flagged"]:
            if self.log_detections:
                logger.warning(f"🚨 TOXIC CONTENT DETECTED in user input")
                for category, score in toxicity_result["categories"].items():
                    logger.warning(f"   {category}: {score:.3f}")

            if self.block_toxic_input:
                # For a child-focused application, use a child-friendly response
                return {
                    "messages": [AIMessage(
                        content="I'm sorry, but I can't respond to that. Please ask me something else that's appropriate for children.",
                        additional_kwargs={
                            'failure_mode': 'toxic_content'
                        }
                    )],
                    "jump_to": "end"
                }

        return None

    @hook_config(can_jump_to=["end"])
    def after_agent(self, state: AgentState, runtime: Runtime) -> dict[str, any] | None:
        """Check for toxicity in agent responses"""
        if not self.sanitize_toxic_output:
            return None

        messages = state.get('messages', [])
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]

        if not ai_messages:
            return None

        last_ai_message = ai_messages[-1]
        content = last_ai_message.content

        # Check for toxicity in AI response
        toxicity_result = self.check_toxicity(content)

        if toxicity_result["flagged"]:
            if self.log_detections:
                logger.warning(f"🚨 TOXIC CONTENT DETECTED in agent response")
                for category, score in toxicity_result["categories"].items():
                    logger.warning(f"   {category}: {score:.3f}")

            # Replace with safe content
            safe_message = AIMessage(
                content="I apologize, but I need to provide a different response. How else can I help you today?",
                additional_kwargs={
                    'failure_mode': 'toxic_response_sanitized'
                }
            )

            # Replace the last AI message with our safe one
            messages = [m if m != last_ai_message else safe_message for m in messages]

            return {"messages": messages}

        return None