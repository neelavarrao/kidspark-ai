from langchain.agents.middleware import AgentMiddleware, AgentState, hook_config
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.runtime import Runtime
from openai import OpenAI
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OnTopicMiddleware(AgentMiddleware):
    """
    Middleware to ensure conversations stay on relevant parenting and child-focused topics.
    This helps keep the AI within its specialized domain and prevent off-topic discussions.
    """

    def __init__(self, topics: list[str] = None):
        """
        Args:
            topics: List of approved topics for conversation
        """
        super().__init__()

        # Default KidSpark topics if none provided
        self.topics = topics or [
            "activities for children",
            "parenting advice",
            "bedtime stories",
            "children's education",
            "child development",
            "games for kids",
            "crafts for children",
            "child behavior",
            "learning activities",
            "children's health",
            "children's safety",
            "children's entertainment",
            "children's books",
            "children's songs",
            "children's movies",
            "toddler activities",
            "preschool activities",
            "children's nutrition",
            "child psychology",
            "parenting questions",
            "why questions from children",
            "helping children learn", "story",
        ]

        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    def check_on_topic(self, text: str) -> dict:
        """
        Check if the provided text is on topic for KidSpark AI

        Returns:
            dict with 'on_topic' (bool) key
        """
        if not isinstance(text, str) or not text.strip():
            return {"on_topic": True}  # Empty content passes by default

        try:
            # Format the topics list for the LLM
            topics_str = ", ".join(self.topics)

            classification_response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use a smaller model for efficiency
                messages=[
                    {"role": "system", "content": f"""
                        You are a topic classifier for a parenting and children's assistant called KidSpark AI.
                        Your job is to determine if the user's message is related to any of these topics:
                        {topics_str}

                        Return only TRUE or FALSE - TRUE if the message is related to children, parenting,
                        or any of the topics listed above, FALSE otherwise.
                    """},
                    {"role": "user", "content": text}
                ],
                max_tokens=5,
                temperature=0
            )

            classification = classification_response.choices[0].message.content.strip().lower()
            print(f"Classification response: {classification}")
            logger.info(f"On-topic check: {classification} for message: {text[:50]}...")

            # Consider "true" in any form as on-topic
            return {
                "on_topic": "true" in classification.lower()
            }
        except Exception as e:
            logger.error(f"Error checking if on topic: {str(e)}")
            return {"on_topic": True}  # Default to passing if there's an error

    @hook_config(can_jump_to=["end"])
    def before_agent(self, state: AgentState, runtime: Runtime) -> dict[str, any] | None:
        """Check if the user's message is on topic before agent processing"""
        messages = state.get('messages', [])
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]

        if not human_messages:
            return None

        last_human_message = human_messages[-1]
        content = last_human_message.content

        # Check if message is on topic
        on_topic_result = self.check_on_topic(content)
        if not on_topic_result["on_topic"]:
            # Use child-friendly language for off-topic response
            return {
                "messages": [AIMessage(
                    content="I'm here to help with questions about children, parenting, and fun activities! Could you ask me something about those topics?",
                    additional_kwargs={
                        'failure_mode': 'off_topic'
                    }
                )],
                "jump_to": "end"
            }

        return None