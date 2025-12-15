"""
Story Agent for KidSpark AI
Uses RAG (Retrieval-Augmented Generation) to find and present personalized bedtime stories.
Implements middleware architecture for tracing, toxicity detection, and topic relevance.
"""

from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from typing import Optional, List, Dict
import logging
import json
import uuid

from app.backend.agents.middleware.tracing import TracingMiddleware
from app.backend.agents.middleware.toxicity import ToxicityDetectionMiddleware
from app.backend.agents.middleware.on_topic import OnTopicMiddleware
from app.backend.agents.services.embedding_service import get_embedding
from app.backend.services.supabase_service import get_supabase_client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# System prompt for the Story Agent
STORY_AGENT_SYSTEM_PROMPT = """You are a friendly storytelling assistant for KidSpark AI.
Your role is to help parents find the perfect bedtime story for their children.

IMPORTANT: When a user asks for a story, you MUST:
1. IMMEDIATELY use the search_stories tool with the user's request as the query
2. DO NOT ask clarifying questions - just search with whatever information is provided
3. After finding stories, use get_story to retrieve the full story text for the best match
4. Present the story text directly to the user

You have access to these tools:
- search_stories: Search for stories by theme, topic, or description. ALWAYS use this first.
- get_story: Get the full story text by ID after finding a match.

Example workflow:
- User says "tell me a story about kindness" -> Use search_stories(query="kindness") -> Use get_story(story_id=<best_match_id>) -> Return the story

Guidelines:
- Always be child-appropriate and supportive of positive parenting
- If no matching story is found, apologize and suggest trying themes like: adventure, princess, dinosaur, space, animals, magic
- Present stories in a warm, engaging format
- DO NOT ask for age or other details unless the search returns no results

Remember: Your primary job is to find and present stories, not to have conversations!
"""


# Reranking prompt template
RERANK_PROMPT = """Given the user's story request and the following story candidates, select the BEST matching story.

User's request: {user_query}

Story candidates:
{stories_formatted}

Consider:
1. Theme relevance to user's request
2. Age appropriateness (if mentioned)
3. Moral lesson alignment with what the user might want
4. Story setting and characters match

Respond with ONLY the story ID number of the best match. Nothing else."""


class StoryAgent:
    """
    Story Agent that uses RAG to find and present personalized bedtime stories.
    Uses middleware architecture for tracing, toxicity detection, and topic relevance.
    """

    def __init__(self, model_name: str = "gpt-4o", run_id: str = None, user_id: str = None):
        """
        Initialize the Story Agent.

        Args:
            model_name: The OpenAI model to use
            run_id: Unique identifier for this conversation run
            user_id: ID of the user making the request
        """
        self.llm = ChatOpenAI(model=model_name)
        self.rerank_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)  # Faster model for reranking
        self.agent = None
        self.run_id = run_id or str(uuid.uuid4())
        self.user_id = user_id
        self.message_history = []
        self.supabase = get_supabase_client()
        self.system_prompt = STORY_AGENT_SYSTEM_PROMPT

    def record_story_shown(self, story_id: int, user_id: str = None) -> bool:
        """
        Record that a story was shown to a user in the user_story_history table.

        Args:
            story_id: The ID of the story that was shown
            user_id: The user ID (uses self.user_id if not provided)

        Returns:
            True if recording was successful, False otherwise
        """
        effective_user_id = user_id or self.user_id

        if not effective_user_id:
            logger.warning("Cannot record story history: no user_id provided")
            return False

        try:
            # Insert into user_story_history (upsert to handle duplicates)
            response = self.supabase.table('user_story_history').upsert({
                'user_id': effective_user_id,
                'story_id': story_id,
                'shown_at': 'now()'
            }, on_conflict='user_id,story_id').execute()

            logger.info(f"Recorded story {story_id} shown to user {effective_user_id}")
            return True

        except Exception as e:
            logger.error(f"Error recording story history: {str(e)}")
            return False

    def get_user_story_history(self, user_id: str = None) -> List[int]:
        """
        Get list of story IDs that have been shown to a user.

        Args:
            user_id: The user ID (uses self.user_id if not provided)

        Returns:
            List of story IDs the user has seen
        """
        effective_user_id = user_id or self.user_id

        if not effective_user_id:
            return []

        try:
            response = self.supabase.table('user_story_history').select(
                'story_id'
            ).eq('user_id', effective_user_id).execute()

            if response.data:
                return [record['story_id'] for record in response.data]
            return []

        except Exception as e:
            logger.error(f"Error fetching story history: {str(e)}")
            return []

    async def initialize(self):
        """Initialize the agent with tools and middleware stack"""
        try:
            logger.info(f"Initializing StoryAgent with run_id: {self.run_id}")

            # Define the tools for this agent
            tools = [self._create_search_stories_tool(), self._create_get_story_tool()]

            # Create agent with middleware stack
            self.agent = create_agent(
                model=self.llm,
                tools=tools,
                system_prompt=self.system_prompt,
                middleware=[
                    TracingMiddleware(
                        run_id=self.run_id,
                        agent_id='story_agent',
                        user_id=self.user_id
                    ),
                    ToxicityDetectionMiddleware(
                        block_toxic_input=True,
                        sanitize_toxic_output=True,
                        log_detections=True,
                        toxicity_threshold=0.3  # Lower threshold for child safety
                    ),
                    OnTopicMiddleware()  # Uses default KidSpark topics
                ]
            )

            logger.info("StoryAgent initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing StoryAgent: {str(e)}")
            raise

    def _create_search_stories_tool(self):
        """Create the search_stories tool for the agent"""
        supabase = self.supabase

        @tool
        def search_stories(query: str, child_age: Optional[int] = None) -> str:
            """
            Search for stories matching the user's request using semantic similarity.

            Args:
                query: The user's story request (e.g., "adventure story about a brave knight")
                child_age: Optional age of the child to filter age-appropriate stories

            Returns:
                JSON string containing matching stories with their metadata
            """
            try:
                logger.info(f"Searching stories for query: {query}, age: {child_age}")

                # Generate embedding for the query
                query_embedding = get_embedding(query)

                # Prepare RPC parameters
                rpc_params = {
                    'query_embedding': query_embedding,
                    'match_threshold': 0.1,  # Lower threshold to get more candidates for reranking
                    'match_count': 5
                }

                # Add age filter if provided
                if child_age:
                    rpc_params['min_age'] = max(0, child_age - 1)  # Allow 1 year below
                    rpc_params['max_age'] = child_age + 2  # Allow 2 years above

                # Call the enhanced match function
                response = supabase.rpc('match_stories_enhanced', rpc_params).execute()
                print(response)
                if response.data and len(response.data) > 0:
                    logger.info(f"Found {len(response.data)} matching stories")
                    # Return stories with metadata for reranking
                    stories = []
                    for story in response.data:
                        stories.append({
                            'id': story['id'],
                            'title': story['story_title'],
                            'moral_lesson': story['moral_lesson'],
                            'lesson_summary': story['lesson_summary'],
                            'age_range': f"{story['age_range_min']}-{story['age_range_max']}",
                            'setting': story['setting'],
                            'characters': story['characters'],
                            'duration_minutes': story['duration_minutes'],
                            'similarity': story['similarity']
                        })
                    return json.dumps(stories, indent=2)
                else:
                    logger.info("No matching stories found")
                    return json.dumps({"message": "No matching stories found. Try a different theme or description."})

            except Exception as e:
                logger.error(f"Error searching stories: {str(e)}")
                return json.dumps({"error": f"Error searching stories: {str(e)}"})

        return search_stories

    def _create_get_story_tool(self):
        """Create the get_story tool to retrieve full story text"""
        supabase = self.supabase

        @tool
        def get_story(story_id: int) -> str:
            """
            Retrieve the full story text for a given story ID.

            Args:
                story_id: The ID of the story to retrieve

            Returns:
                The full story text with title and moral lesson
            """
            try:
                logger.info(f"Retrieving story with ID: {story_id}")

                response = supabase.table('stories').select(
                    'story_title, story_text, moral_lesson, discussion_questions'
                ).eq('id', story_id).execute()

                if response.data and len(response.data) > 0:
                    story = response.data[0]
                    logger.info(f"Retrieved story: {story['story_title']}")

                    # Format the story nicely
                    formatted_story = f"""
# {story['story_title']}

{story['story_text']}

---
**Moral of the story:** {story['moral_lesson']}
"""
                    return formatted_story
                else:
                    return "Story not found. Please try searching for a different story."

            except Exception as e:
                logger.error(f"Error retrieving story: {str(e)}")
                return f"Error retrieving story: {str(e)}"

        return get_story

    async def rerank_stories(self, user_query: str, stories: List[Dict]) -> Optional[int]:
        """
        Use LLM to rerank stories and select the best match.

        Args:
            user_query: The original user query
            stories: List of story candidates with metadata

        Returns:
            The ID of the best matching story, or None if reranking fails
        """
        if not stories:
            return None

        if len(stories) == 1:
            return stories[0]['id']

        try:
            # Format stories for the reranking prompt
            stories_formatted = "\n\n".join([
                f"ID: {s['id']}\n"
                f"Title: {s['title']}\n"
                f"Moral: {s['moral_lesson']}\n"
                f"Summary: {s['lesson_summary']}\n"
                f"Age Range: {s['age_range']}\n"
                f"Setting: {s['setting']}\n"
                f"Similarity Score: {s['similarity']:.3f}"
                for s in stories
            ])

            prompt = RERANK_PROMPT.format(
                user_query=user_query,
                stories_formatted=stories_formatted
            )

            response = self.rerank_llm.invoke([HumanMessage(content=prompt)])
            selected_id = int(response.content.strip())

            logger.info(f"Reranking selected story ID: {selected_id}")
            return selected_id

        except Exception as e:
            logger.error(f"Error during reranking: {str(e)}")
            # Fallback to highest similarity score
            return stories[0]['id']

    async def handle_message(self, user_message: str) -> str:
        """
        Handle a user message requesting a story.

        Args:
            user_message: The user's message

        Returns:
            The agent's response (typically the story text)
        """
        try:
            # Initialize agent if not already done
            if self.agent is None:
                await self.initialize()

            logger.info(f"Processing story request: {user_message[:50]}...")

            # Add the user message to history
            self.message_history.append(HumanMessage(content=user_message))

            # Invoke the agent with message history
            result = await self.agent.ainvoke({
                "messages": self.message_history
            })

            # Update message history with full conversation
            self.message_history = result['messages']

            # Extract the final response
            response = result['messages'][-1].content
            logger.info("Story response generated successfully")

            return response

        except Exception as e:
            logger.error(f"Error processing story request: {str(e)}")
            return f"I'm sorry, I had trouble finding a story for you. Could you try asking in a different way? Error: {str(e)}"

    async def get_story_directly(self, user_query: str, child_age: Optional[int] = None) -> str:
        """
        Simplified method to get a story directly without the full agent loop.
        Useful for testing or when you want to bypass the agent.

        Args:
            user_query: What kind of story the user wants
            child_age: Optional age of the child

        Returns:
            The story text or an error message
        """
        try:
            # Generate embedding
            query_embedding = get_embedding(user_query)

            # Search for stories
            rpc_params = {
                'query_embedding': query_embedding,
                'match_threshold': 0.5,
                'match_count': 5
            }

            if child_age:
                rpc_params['min_age'] = max(0, child_age - 1)
                rpc_params['max_age'] = child_age + 2

            response = self.supabase.rpc('match_stories_enhanced', rpc_params).execute()

            if not response.data:
                return "I couldn't find a story matching your request. Try asking for a different theme like adventure, princess, dinosaur, or magic!"

            # Rerank stories
            stories = [{
                'id': s['id'],
                'title': s['story_title'],
                'moral_lesson': s['moral_lesson'],
                'lesson_summary': s['lesson_summary'],
                'age_range': f"{s['age_range_min']}-{s['age_range_max']}",
                'setting': s['setting'],
                'similarity': s['similarity']
            } for s in response.data]

            best_story_id = await self.rerank_stories(user_query, stories)

            if not best_story_id:
                best_story_id = stories[0]['id']

            # Get full story
            story_response = self.supabase.table('stories').select(
                'story_title, story_text, moral_lesson'
            ).eq('id', best_story_id).execute()

            if story_response.data:
                story = story_response.data[0]
                return f"""# {story['story_title']}

{story['story_text']}

---
**Moral of the story:** {story['moral_lesson']}
"""

            return "Story not found."

        except Exception as e:
            logger.error(f"Error in get_story_directly: {str(e)}")
            return f"I'm sorry, something went wrong while finding your story. Error: {str(e)}"

    async def get_story_with_metadata(self, user_query: str, child_age: Optional[int] = None) -> Dict:
        """
        Get a story with full metadata for the story viewer modal.

        Args:
            user_query: What kind of story the user wants
            child_age: Optional age of the child

        Returns:
            Dict with story data formatted for the UI modal, or error info
        """
        try:
            # Generate embedding
            query_embedding = get_embedding(user_query)

            # Search for stories
            rpc_params = {
                'query_embedding': query_embedding,
                'match_threshold': 0.1,
                'match_count': 5
            }

            if child_age:
                rpc_params['min_age'] = max(0, child_age - 1)
                rpc_params['max_age'] = child_age + 2

            response = self.supabase.rpc('match_stories_enhanced', rpc_params).execute()

            if not response.data:
                return {
                    "success": False,
                    "message": "I couldn't find a story matching your request. Try asking for a different theme like adventure, princess, dinosaur, or magic!"
                }

            # Get previously seen stories to exclude them
            seen_story_ids = self.get_user_story_history()
            logger.info(f"User has seen {len(seen_story_ids)} stories: {seen_story_ids}")

            # Filter out previously seen stories
            unseen_stories = [s for s in response.data if s['id'] not in seen_story_ids]

            # If all stories have been seen, use all stories but log a message
            if not unseen_stories:
                logger.info("User has seen all matching stories, showing a repeat")
                unseen_stories = response.data

            # Rerank stories (only unseen ones)
            stories = [{
                'id': s['id'],
                'title': s['story_title'],
                'moral_lesson': s['moral_lesson'],
                'lesson_summary': s['lesson_summary'],
                'age_range': f"{s['age_range_min']}-{s['age_range_max']}",
                'setting': s['setting'],
                'similarity': s['similarity']
            } for s in unseen_stories]

            best_story_id = await self.rerank_stories(user_query, stories)

            if not best_story_id:
                best_story_id = stories[0]['id']

            # Get full story with all metadata
            story_response = self.supabase.table('stories').select(
                'id, story_title, story_text, moral_lesson, lesson_summary, '
                'age_range_min, age_range_max, characters, setting, '
                'duration_minutes, discussion_questions'
            ).eq('id', best_story_id).execute()

            if story_response.data:
                story = story_response.data[0]

                # Record that this story was shown to the user
                self.record_story_shown(story_id=story['id'])

                # Format for the UI modal
                return {
                    "success": True,
                    "message": f"I found a wonderful story for you: **{story['story_title']}**! Click 'Read Story' to enjoy it.",
                    "story_data": {
                        "id": story['id'],  # Include ID for tracking
                        "title": story['story_title'],
                        "content": story['story_text'],
                        "moral": story['moral_lesson'],
                        "duration": story['duration_minutes'],
                        "age_range": f"{story['age_range_min']}-{story['age_range_max']} years",
                        "setting": story['setting'],
                        "characters": story['characters'] if isinstance(story['characters'], list) else [],
                        "discussion": story['discussion_questions'] if isinstance(story['discussion_questions'], list) else []
                    }
                }

            return {
                "success": False,
                "message": "Story not found. Please try a different request."
            }

        except Exception as e:
            logger.error(f"Error in get_story_with_metadata: {str(e)}")
            return {
                "success": False,
                "message": f"I'm sorry, something went wrong while finding your story. Please try again."
            }


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def main():
        # Create story agent
        agent = StoryAgent()

        # Test queries
        test_queries = [
            "tell me a story about kindness",
        ]

        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"User: {query}")
            print(f"{'='*60}")
            response = await agent.handle_message(query)
            print(f"Agent: {response[:500]}...")  # Truncate for display

    asyncio.run(main())
