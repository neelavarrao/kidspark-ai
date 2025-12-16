"""
Why Agent for KidSpark AI
Provides child-friendly explanations to curious "why" questions.
Uses age-appropriate language and engaging analogies.
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from typing import Optional, Dict, List
import logging
import uuid

from app.backend.agents.middleware.tracing import TracingMiddleware
from app.backend.agents.middleware.toxicity import ToxicityDetectionMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Age-specific guidelines
AGE_GUIDELINES = {
    "3-4": """For ages 3-4:
- Use VERY simple words (1-2 syllables when possible)
- Maximum 2 short sentences
- Use comparisons to things they know: toys, food, family, animals, home
- Example: "The sun is like a big warm lamp that lives in the sky!"
- Avoid any complex concepts""",

    "5-6": """For ages 5-6:
- Use simple words but can introduce one new word with explanation
- 2-3 sentences maximum
- Can explain simple cause and effect
- Use fun analogies: "It's like when you..."
- Example: "Clouds are like big fluffy sponges that hold water. When they get too full, the water falls down as rain!"
""",

    "7+": """For ages 7+:
- Can use slightly more detailed explanations
- 3-4 sentences maximum
- Can introduce basic science terms if you explain them simply
- Can handle slightly more abstract concepts
- Example: "Plants are green because of something called chlorophyll - it's like tiny green helpers inside the leaves that catch sunlight to make food for the plant!"
"""
}


# System prompt template for the Why Agent
WHY_AGENT_SYSTEM_PROMPT = """You are Hoot, a friendly and wise owl who LOVES answering questions from curious children! 🦉

Your personality:
- Warm, encouraging, and patient
- You get EXCITED about every question ("Great question!", "Ooh, I love this one!")
- You use fun sounds and expressions

{age_guidelines}

IMPORTANT RULES:
1. ALWAYS start with an encouraging phrase
2. Keep answers SHORT - children have short attention spans
3. Use ONE emoji that relates to the topic in your answer
4. Use analogies to everyday things kids understand
5. Never talk down to kids - treat their questions as important
6. If you don't know something, say "That's a tricky one! You could ask a grown-up to help us find out!"

SENSITIVE TOPICS:
- Death: Be gentle, use nature analogies (flowers, seasons), suggest talking to parents
- Violence: Redirect to kindness, don't explain in detail
- Adult themes: Give very simple answer, suggest asking parents for more
- Scary things: Acknowledge feelings, provide comfort, keep it light

NEVER include:
- Complex jargon without explanation
- Scary or disturbing details
- Anything inappropriate for children
- Long paragraphs of text

Remember: You're helping spark curiosity and make learning FUN! 🌟"""


# Follow-up prompt for "Tell Me More"
FOLLOW_UP_PROMPT = """The child wants to know MORE about this topic.

Previous question: {previous_question}
Your previous answer: {previous_answer}

Now give ONE more interesting detail or fun fact about this topic.
Keep it short (1-2 sentences) and age-appropriate.
Start with something like "Here's something cool..." or "Did you know..."
Include a relevant emoji."""


class WhyAgent:
    """
    Why Agent that provides child-friendly explanations to curious questions.
    Adapts language complexity based on age group.
    """

    def __init__(self, model_name: str = "gpt-4o", run_id: str = None, user_id: str = None):
        """
        Initialize the Why Agent.

        Args:
            model_name: The OpenAI model to use
            run_id: Unique identifier for this session
            user_id: ID of the user making the request
        """
        self.llm = ChatOpenAI(model=model_name, temperature=0.7)  # Slightly creative
        self.run_id = run_id or str(uuid.uuid4())
        self.user_id = user_id
        self.conversation_history: List[Dict] = []  # Track Q&A for follow-ups

        # Initialize middleware
        self.tracing = TracingMiddleware(
            run_id=self.run_id,
            agent_id='why_agent',
            user_id=self.user_id
        )
        self.toxicity = ToxicityDetectionMiddleware(
            block_toxic_input=True,
            sanitize_toxic_output=True,
            log_detections=True,
            toxicity_threshold=0.3  # Strict for child safety
        )

    def _get_system_prompt(self, age_group: str) -> str:
        """Get the system prompt customized for the age group."""
        age_guidelines = AGE_GUIDELINES.get(age_group, AGE_GUIDELINES["5-6"])
        return WHY_AGENT_SYSTEM_PROMPT.format(age_guidelines=age_guidelines)

    async def check_input_safety(self, question: str) -> Dict:
        """
        Check if the input question is safe/appropriate.

        Returns:
            Dict with 'safe' boolean and optional 'message' if blocked
        """
        try:
            # Use toxicity middleware to check input
            is_toxic, toxicity_score = await self.toxicity._check_toxicity(question)

            if is_toxic:
                logger.warning(f"Toxic input detected in why question: {question[:50]}...")
                return {
                    "safe": False,
                    "message": "Hmm, let's ask a different question! What else are you curious about? 🦉"
                }

            return {"safe": True}

        except Exception as e:
            logger.error(f"Error checking input safety: {str(e)}")
            # Default to safe if check fails, LLM will handle appropriately
            return {"safe": True}

    async def answer_question(
        self,
        question: str,
        age_group: str = "5-6",
        is_follow_up: bool = False
    ) -> Dict:
        """
        Answer a "why" question with an age-appropriate explanation.

        Args:
            question: The child's question
            age_group: Age range ("3-4", "5-6", or "7+")
            is_follow_up: Whether this is a "Tell Me More" request

        Returns:
            Dict with 'success', 'answer', and optionally 'fun_fact'
        """
        try:
            logger.info(f"Why question received: {question[:50]}... (age: {age_group}, follow_up: {is_follow_up})")

            # Check input safety
            safety_check = await self.check_input_safety(question)
            if not safety_check["safe"]:
                return {
                    "success": True,
                    "answer": safety_check["message"],
                    "can_follow_up": False
                }

            # Build messages
            messages = [SystemMessage(content=self._get_system_prompt(age_group))]

            if is_follow_up and self.conversation_history:
                # Get the last Q&A for context
                last_qa = self.conversation_history[-1]
                follow_up_content = FOLLOW_UP_PROMPT.format(
                    previous_question=last_qa["question"],
                    previous_answer=last_qa["answer"]
                )
                messages.append(HumanMessage(content=follow_up_content))
            else:
                # Regular question
                messages.append(HumanMessage(content=f"Why question from a curious child: {question}"))

            # Get response from LLM
            response = await self.llm.ainvoke(messages)
            answer = response.content

            # Store in conversation history
            self.conversation_history.append({
                "question": question,
                "answer": answer,
                "age_group": age_group
            })

            # Keep only last 5 Q&A pairs
            if len(self.conversation_history) > 5:
                self.conversation_history = self.conversation_history[-5:]

            logger.info(f"Why answer generated successfully")

            return {
                "success": True,
                "answer": answer,
                "can_follow_up": True,
                "question": question
            }

        except Exception as e:
            logger.error(f"Error answering why question: {str(e)}")
            return {
                "success": False,
                "answer": "Oops! My owl brain got a little confused. Can you ask me again? 🦉",
                "can_follow_up": False
            }

    def clear_history(self):
        """Clear the conversation history for a fresh start."""
        self.conversation_history = []
        logger.info("Why agent conversation history cleared")


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def main():
        agent = WhyAgent()

        test_questions = [
            ("Why is the sky blue?", "5-6"),
            ("Why do dogs bark?", "3-4"),
            ("Why do we need to sleep?", "7+"),
        ]

        for question, age in test_questions:
            print(f"\n{'='*60}")
            print(f"Question ({age}): {question}")
            print(f"{'='*60}")
            response = await agent.answer_question(question, age)
            print(f"Hoot says: {response['answer']}")

    asyncio.run(main())
