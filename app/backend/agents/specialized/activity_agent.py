"""
Activity Agent for KidSpark AI
Uses LangChain agent architecture with middleware for guardrails.
Suggests personalized activities for children based on user preferences.
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
from app.backend.services.supabase_service import get_supabase_client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# System prompt for the Activity Agent
ACTIVITY_AGENT_SYSTEM_PROMPT = """You are a helpful activity assistant for KidSpark AI.
Your role is to help parents find engaging, safe, and age-appropriate activities for their children.

IMPORTANT: When a user asks for an activity, you MUST:
1. IMMEDIATELY use the search_activities tool with the user's request
2. DO NOT ask clarifying questions - just search with whatever information is provided
3. After finding activities, use get_activity to retrieve the full details for the best match
4. After calling get_activity, respond with ONLY a SHORT announcement like:
   "I found a great activity for you: **[Activity Name]**! Click 'View Activity' to see the details."

CRITICAL: Do NOT include the full activity details in your response. The activity will be displayed in a popup modal.
Just announce that you found the activity and mention its name.

You have access to these tools:
- search_activities: Search for activities by age, duration, category, or description. ALWAYS use this first.
- get_activity: Get the full activity details by ID after finding a match.

Example workflow:
- User says "activity for my 3 year old" -> Use search_activities(child_age=3) -> Use get_activity(activity_id=<best_match_id>) -> Respond: "I found a great activity for you: **Rainbow Rice Sensory Bin**! Click 'View Activity' to see the details."

Guidelines:
- ALWAYS recommend safe, child-appropriate activities
- NEVER suggest activities that could be dangerous or harmful
- If asked about dangerous activities (fire, sharp objects, heights, etc.), politely redirect to safe alternatives
- Keep your response SHORT - just announce the activity name
- DO NOT ask for age or other details unless the search returns no results

Remember: Your job is to find activities and announce them briefly. The full details display in a modal!
"""


# Reranking prompt template
ACTIVITY_RERANK_PROMPT = """Given the user's activity request and the following candidates, select the BEST and SAFEST activity.

User's request: {user_query}

Activity candidates:
{activities_formatted}

Consider:
1. SAFETY - Is this activity safe for the child's age?
2. Age appropriateness
3. Time constraints mentioned by user
4. Location preference (indoor/outdoor)
5. Materials likely available at home
6. Educational value and engagement level

Respond with ONLY the activity ID number of the best match. Nothing else."""


# Category mappings for indoor/outdoor filtering
INDOOR_CATEGORIES = ["sensory", "fine_motor", "art", "music", "pretend_play", "cognitive", "reading"]
OUTDOOR_CATEGORIES = ["gross_motor", "nature", "water_play", "outdoor_exploration"]


class ActivityAgent:
    """
    Activity Agent that uses LangChain agent architecture with middleware.
    Suggests personalized activities for children with guardrails for safety.
    """

    def __init__(self, model_name: str = "gpt-4o", run_id: str = None, user_id: str = None):
        """
        Initialize the Activity Agent.

        Args:
            model_name: The OpenAI model to use
            run_id: Unique identifier for this conversation run
            user_id: ID of the user making the request
        """
        self.llm = ChatOpenAI(model=model_name)
        self.rerank_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        self.agent = None
        self.run_id = run_id or str(uuid.uuid4())
        self.user_id = user_id
        self.message_history = []
        self.supabase = get_supabase_client()
        self.system_prompt = ACTIVITY_AGENT_SYSTEM_PROMPT
        self.last_activity_data = None  # Store the last retrieved activity for modal display

    async def initialize(self):
        """Initialize the agent with tools and middleware stack"""
        try:
            logger.info(f"Initializing ActivityAgent with run_id: {self.run_id}")

            # Define the tools for this agent
            tools = [self._create_search_activities_tool(), self._create_get_activity_tool()]

            # Create agent with middleware stack
            self.agent = create_agent(
                model=self.llm,
                tools=tools,
                system_prompt=self.system_prompt,
                middleware=[
                    TracingMiddleware(
                        run_id=self.run_id,
                        agent_id='activity_agent',
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

            logger.info("ActivityAgent initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing ActivityAgent: {str(e)}")
            raise

    def record_activity_shown(self, activity_id: int, user_id: str = None) -> bool:
        """
        Record that an activity was shown to a user in the user_activity_history table.

        Args:
            activity_id: The ID of the activity that was shown
            user_id: The user ID (uses self.user_id if not provided)

        Returns:
            True if recording was successful, False otherwise
        """
        effective_user_id = user_id or self.user_id

        if not effective_user_id:
            logger.warning("Cannot record activity history: no user_id provided")
            return False

        try:
            # Insert into user_activity_history (upsert to handle duplicates)
            self.supabase.table('user_activity_history').upsert({
                'user_id': effective_user_id,
                'activity_id': activity_id,
                'shown_at': 'now()'
            }, on_conflict='user_id,activity_id').execute()

            logger.info(f"Recorded activity {activity_id} shown to user {effective_user_id}")
            return True

        except Exception as e:
            logger.error(f"Error recording activity history: {str(e)}")
            return False

    def get_user_activity_history(self, user_id: str = None) -> List[int]:
        """
        Get list of activity IDs that have been shown to a user.

        Args:
            user_id: The user ID (uses self.user_id if not provided)

        Returns:
            List of activity IDs the user has seen
        """
        effective_user_id = user_id or self.user_id

        if not effective_user_id:
            return []

        try:
            response = self.supabase.table('user_activity_history').select(
                'activity_id'
            ).eq('user_id', effective_user_id).execute()

            if response.data:
                return [record['activity_id'] for record in response.data]
            return []

        except Exception as e:
            logger.error(f"Error fetching activity history: {str(e)}")
            return []

    def _create_search_activities_tool(self):
        """Create the search_activities tool for the agent"""
        supabase = self.supabase

        @tool
        def search_activities(
            child_age: Optional[int] = None,
            max_duration: Optional[int] = None,
            location: Optional[str] = None
        ) -> str:
            """
            Search for activities matching the user's request.

            Args:
                child_age: Age of the child (optional)
                max_duration: Maximum duration in minutes (optional)
                location: "indoor" or "outdoor" preference (optional)

            Returns:
                JSON string containing matching activities with their metadata
            """
            try:
                logger.info(f"Searching activities: age={child_age}, duration={max_duration}, location={location}")

                # Build query
                query_builder = supabase.table('activities').select(
                    'id, activity_name, activity_category, materials, '
                    'age_range_min, age_range_max, duration_minutes, prep_time_minutes, '
                    'description'
                )

                # Apply filters
                if child_age is not None:
                    query_builder = query_builder.lte('age_range_min', child_age).gte('age_range_max', child_age)

                if max_duration is not None:
                    query_builder = query_builder.lte('duration_minutes', max_duration)

                # Location-based category filtering
                if location == "indoor":
                    query_builder = query_builder.in_('activity_category', INDOOR_CATEGORIES)
                elif location == "outdoor":
                    query_builder = query_builder.in_('activity_category', OUTDOOR_CATEGORIES)

                # Limit results
                query_builder = query_builder.limit(10)

                response = query_builder.execute()

                if response.data and len(response.data) > 0:
                    logger.info(f"Found {len(response.data)} matching activities")
                    activities = []
                    for activity in response.data:
                        activities.append({
                            'id': activity['id'],
                            'name': activity['activity_name'],
                            'category': activity['activity_category'],
                            'age_range': f"{activity['age_range_min']}-{activity['age_range_max']}",
                            'duration': activity['duration_minutes'],
                            'prep_time': activity['prep_time_minutes'],
                            'description': activity['description'],
                            'materials': activity['materials']
                        })
                    return json.dumps(activities, indent=2)
                else:
                    logger.info("No matching activities found")
                    return json.dumps({"message": "No matching activities found. Try different criteria."})

            except Exception as e:
                logger.error(f"Error searching activities: {str(e)}")
                return json.dumps({"error": f"Error searching activities: {str(e)}"})

        return search_activities

    def _create_get_activity_tool(self):
        """Create the get_activity tool to retrieve full activity details"""
        supabase = self.supabase
        agent_instance = self  # Reference to store activity data

        @tool
        def get_activity(activity_id: int) -> str:
            """
            Retrieve the full activity details for a given activity ID.

            Args:
                activity_id: The ID of the activity to retrieve

            Returns:
                The full activity details with instructions and variations
            """
            try:
                logger.info(f"Retrieving activity with ID: {activity_id}")

                response = supabase.table('activities').select(
                    'id, activity_name, activity_category, materials, '
                    'age_range_min, age_range_max, duration_minutes, prep_time_minutes, '
                    'description, parent_instruction, variations'
                ).eq('id', activity_id).execute()

                if response.data and len(response.data) > 0:
                    activity = response.data[0]
                    logger.info(f"Retrieved activity: {activity['activity_name']}")

                    # Format the activity nicely
                    materials_list = activity['materials'] if isinstance(activity['materials'], list) else []
                    variations_list = activity['variations'] if isinstance(activity['variations'], list) else []

                    # Store activity data for modal display
                    agent_instance.last_activity_data = {
                        "id": activity['id'],
                        "name": activity['activity_name'],
                        "category": activity['activity_category'].replace('_', ' ').title(),
                        "materials": materials_list,
                        "duration": activity['duration_minutes'],
                        "prep_time": activity['prep_time_minutes'],
                        "age_range": f"{activity['age_range_min']}-{activity['age_range_max']} years",
                        "description": activity['description'],
                        "instructions": activity['parent_instruction'],
                        "variations": variations_list
                    }

                    # Record that this activity was shown to the user
                    agent_instance.record_activity_shown(activity_id=activity['id'])

                    formatted_activity = f"""
# {activity['activity_name']}

**Category:** {activity['activity_category'].replace('_', ' ').title()}
**Age Range:** {activity['age_range_min']}-{activity['age_range_max']} years
**Duration:** {activity['duration_minutes']} minutes
**Prep Time:** {activity['prep_time_minutes']} minutes

## Materials Needed
{chr(10).join(['- ' + m for m in materials_list]) if materials_list else '- No specific materials needed'}

## Description
{activity['description']}

## Parent Instructions
{activity['parent_instruction']}

## Variations to Try
{chr(10).join(['- ' + v for v in variations_list]) if variations_list else '- Get creative with your own variations!'}
"""
                    return formatted_activity
                else:
                    agent_instance.last_activity_data = None
                    return "Activity not found. Please try searching for a different activity."

            except Exception as e:
                logger.error(f"Error retrieving activity: {str(e)}")
                agent_instance.last_activity_data = None
                return f"Error retrieving activity: {str(e)}"

        return get_activity

    async def rerank_activities(self, user_query: str, activities: List[Dict]) -> Optional[int]:
        """
        Use LLM to rerank activities and select the best match.

        Args:
            user_query: The original user query
            activities: List of activity candidates with metadata

        Returns:
            The ID of the best matching activity, or None if reranking fails
        """
        if not activities:
            return None

        if len(activities) == 1:
            return activities[0]['id']

        try:
            # Format activities for the reranking prompt
            activities_formatted = "\n\n".join([
                f"ID: {a['id']}\n"
                f"Name: {a.get('activity_name', 'Unknown')}\n"
                f"Category: {a.get('activity_category', 'Unknown')}\n"
                f"Age Range: {a.get('age_range_min', '?')}-{a.get('age_range_max', '?')} years\n"
                f"Duration: {a.get('duration_minutes', '?')} minutes\n"
                f"Description: {a.get('description', 'No description')}"
                for a in activities
            ])

            prompt = ACTIVITY_RERANK_PROMPT.format(
                user_query=user_query,
                activities_formatted=activities_formatted
            )

            response = self.rerank_llm.invoke([HumanMessage(content=prompt)])
            selected_id = int(response.content.strip())

            logger.info(f"Reranking selected activity ID: {selected_id}")
            return selected_id

        except Exception as e:
            logger.error(f"Error during reranking: {str(e)}")
            # Fallback to first activity
            return activities[0]['id']

    async def handle_message(self, user_message: str) -> Dict:
        """
        Handle a user message requesting an activity using the LangChain agent.
        Middleware (toxicity, on-topic) is applied automatically by the agent.

        Args:
            user_message: The user's message

        Returns:
            Dict with 'success', 'message', and optionally 'activity_data' for modal display
        """
        try:
            # Initialize agent if not already done
            if self.agent is None:
                await self.initialize()

            logger.info(f"Processing activity request: {user_message[:50]}...")

            # Clear any previous activity data
            self.last_activity_data = None

            # Add the user message to history
            self.message_history.append(HumanMessage(content=user_message))

            # Invoke the agent with message history
            # Middleware is applied automatically by create_agent
            result = await self.agent.ainvoke({
                "messages": self.message_history
            })

            # Update message history with full conversation
            self.message_history = result['messages']

            # Extract the final response
            response = result['messages'][-1].content
            logger.info("Activity response generated successfully")

            # Return response with activity data if available
            result_dict = {
                "success": True,
                "message": response
            }

            # If an activity was retrieved by the tool, include it for modal display
            if self.last_activity_data:
                result_dict["activity_data"] = self.last_activity_data

            return result_dict

        except Exception as e:
            logger.error(f"Error processing activity request: {str(e)}")
            return {
                "success": False,
                "message": f"I'm sorry, I had trouble finding an activity for you. Could you try asking in a different way? Error: {str(e)}"
            }

    async def get_activity_with_metadata(
        self,
        user_query: str,
        child_age: Optional[int] = None,
        max_duration: Optional[int] = None,
        location: Optional[str] = None
    ) -> Dict:
        """
        Get an activity with full metadata for the activity viewer modal.
        This method bypasses the agent for direct DB access but still uses middleware for guardrails.

        Args:
            user_query: What kind of activity the user wants
            child_age: Optional age of the child
            max_duration: Optional maximum duration in minutes
            location: Optional "indoor" or "outdoor" preference

        Returns:
            Dict with activity data formatted for the UI modal, or error info
        """
        try:
            # Initialize agent to set up middleware (even though we're not using the full agent flow)
            if self.agent is None:
                await self.initialize()

            # Use the agent's handle_message for guardrail checks
            # The middleware will automatically block toxic/off-topic content
            # But for the modal flow, we do direct DB queries after the check

            # Build query
            query_builder = self.supabase.table('activities').select(
                'id, activity_name, activity_category, materials, '
                'age_range_min, age_range_max, duration_minutes, prep_time_minutes, '
                'description, parent_instruction, variations'
            )

            # Apply filters
            if child_age is not None:
                query_builder = query_builder.lte('age_range_min', child_age).gte('age_range_max', child_age)

            if max_duration is not None:
                query_builder = query_builder.lte('duration_minutes', max_duration)

            # Location-based category filtering
            if location == "indoor":
                query_builder = query_builder.in_('activity_category', INDOOR_CATEGORIES)
            elif location == "outdoor":
                query_builder = query_builder.in_('activity_category', OUTDOOR_CATEGORIES)

            # Limit results
            query_builder = query_builder.limit(10)

            response = query_builder.execute()

            if not response.data:
                return {
                    "success": False,
                    "message": "I couldn't find an activity matching your request. Try asking for a different type of activity or adjust the age/time constraints!"
                }

            # Get previously seen activities to exclude them
            seen_activity_ids = self.get_user_activity_history()
            logger.info(f"User has seen {len(seen_activity_ids)} activities: {seen_activity_ids}")

            # Filter out previously seen activities
            unseen_activities = [a for a in response.data if a['id'] not in seen_activity_ids]

            # If all activities have been seen, use all activities
            if not unseen_activities:
                logger.info("User has seen all matching activities, showing a repeat")
                unseen_activities = response.data

            # Rerank activities
            best_activity_id = await self.rerank_activities(user_query, unseen_activities)

            if not best_activity_id:
                best_activity_id = unseen_activities[0]['id']

            # Get full activity data
            activity_response = self.supabase.table('activities').select(
                'id, activity_name, activity_category, materials, '
                'age_range_min, age_range_max, duration_minutes, prep_time_minutes, '
                'description, parent_instruction, variations'
            ).eq('id', best_activity_id).execute()

            if activity_response.data:
                activity = activity_response.data[0]

                # Record that this activity was shown to the user
                self.record_activity_shown(activity_id=activity['id'])

                # Format for the UI modal
                return {
                    "success": True,
                    "message": f"I found a great activity for you: **{activity['activity_name']}**! Click 'View Activity' to see the details.",
                    "activity_data": {
                        "id": activity['id'],
                        "name": activity['activity_name'],
                        "category": activity['activity_category'].replace('_', ' ').title(),
                        "materials": activity['materials'] if isinstance(activity['materials'], list) else [],
                        "duration": activity['duration_minutes'],
                        "prep_time": activity['prep_time_minutes'],
                        "age_range": f"{activity['age_range_min']}-{activity['age_range_max']} years",
                        "description": activity['description'],
                        "instructions": activity['parent_instruction'],
                        "variations": activity['variations'] if isinstance(activity['variations'], list) else []
                    }
                }

            return {
                "success": False,
                "message": "Activity not found. Please try a different request."
            }

        except Exception as e:
            logger.error(f"Error in get_activity_with_metadata: {str(e)}")
            return {
                "success": False,
                "message": "I'm sorry, something went wrong while finding an activity. Please try again."
            }


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def main():
        # Create activity agent
        agent = ActivityAgent()

        # Test queries
        test_queries = [
            "suggest an activity for my 2 year old",
            "I need a 15 minute indoor activity",
            "outdoor activity for a 3 year old",
        ]

        for query in test_queries:
            print(f"\n{'='*60}")
            print(f"Query: {query}")
            print(f"{'='*60}")
            response = await agent.handle_message(query)
            print(f"Response: {response[:500]}...")

    asyncio.run(main())
