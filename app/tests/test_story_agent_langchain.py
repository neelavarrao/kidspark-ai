"""
Integration test for the StoryAgent with proper LangChain agent usage.
"""

import os
import sys
import asyncio
import unittest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.backend.agents.specialized.story_agent import StoryAgent
from app.backend.agents.models.intent import UserMessage, IntentType

# Configure environment for tests
os.environ["OPENAI_API_KEY"] = os.environ.get("OPENAI_API_KEY", "dummy-key-for-testing")


class TestStoryAgentLangChain(unittest.TestCase):
    """Test the StoryAgent with LangChain agent integration"""

    def setUp(self):
        """Set up test environment"""
        # Create a story agent with mocked dependencies
        self.agent = StoryAgent()

        # Create mock story data
        self.mock_story = {
            'id': 1,
            'story_title': 'The Friendly Dragon',
            'moral_lesson': 'Kindness and friendship',
            'lesson_summary': 'A story about finding friendship in unexpected places',
            'age_range_min': 4,
            'age_range_max': 8,
            'characters': json.dumps([{'name': 'Puff', 'type': 'dragon'}]),
            'setting': 'Magical Forest',
            'duration_minutes': 5,
            'story_text': 'Once upon a time, there was a friendly dragon named Puff...',
            'discussion_questions': json.dumps([
                'What made Puff different from other dragons?',
                'Why were the villagers afraid at first?'
            ]),
            'similarity': 0.85
        }

        # Create a mock user message
        self.user_message = UserMessage(
            content="Can you tell me a bedtime story about dragons?",
            user_id="test-user-123",
            message_id="test-message-123",
            timestamp=datetime.utcnow()
        )

        # Parameters from intent detection
        self.params = {
            "themes": ["dragons", "adventure"],
            "length": "short",
            "age": 5
        }

    @patch.object(StoryAgent, 'initialize_agent')
    @patch.object(StoryAgent, '_get_embedding')
    @patch.object(StoryAgent, '_retrieve_stories')
    @patch.object(StoryAgent, '_check_user_story_history')
    @patch.object(StoryAgent, '_record_story_shown')
    async def test_retrieve_story_langchain_used(
        self, mock_record, mock_check_history, mock_retrieve, mock_embedding, mock_init_agent
    ):
        """Test that retrieve_story calls initialize_agent and works correctly"""
        # Set up mocks
        mock_init_agent.return_value = None
        mock_embedding.return_value = [0.1] * 1536
        mock_retrieve.return_value = [self.mock_story]
        mock_check_history.return_value = []

        # Set the agent's agent object to a mock
        self.agent.agent = AsyncMock()
        self.agent.agent.ainvoke.return_value = {
            "messages": [
                {"role": "user", "content": "Input message"},
                {"role": "assistant", "content": "Here's a wonderful story about The Friendly Dragon!"}
            ]
        }

        # Call retrieve_story
        response = await self.agent.retrieve_story(self.user_message, self.params)

        # Check that the LangChain agent was initialized
        mock_init_agent.assert_called_once()

        # Check that the LangChain agent was invoked
        self.agent.agent.ainvoke.assert_called()

        # Check the response
        self.assertEqual(response.detected_intent, IntentType.STORY)
        self.assertIn("display_type", response.metadata)
        self.assertEqual(response.metadata["display_type"], "story")
        self.assertIn("story_data", response.metadata)
        self.assertEqual(response.metadata["story_data"]["title"], "The Friendly Dragon")

        # Check that story was recorded as shown
        mock_record.assert_called_once_with("test-user-123", 1)

    @patch.object(StoryAgent, 'initialize_agent')
    @patch.object(StoryAgent, '_get_embedding')
    @patch.object(StoryAgent, '_retrieve_stories')
    @patch.object(StoryAgent, '_check_user_story_history')
    async def test_retrieve_story_no_stories_found(
        self, mock_check_history, mock_retrieve, mock_embedding, mock_init_agent
    ):
        """Test retrieve_story behavior when no stories are found"""
        # Set up mocks
        mock_init_agent.return_value = None
        mock_embedding.return_value = [0.1] * 1536
        mock_retrieve.return_value = []  # No stories found
        mock_check_history.return_value = []

        # Set the agent's agent object to a mock
        self.agent.agent = AsyncMock()
        self.agent.agent.ainvoke.return_value = {
            "messages": [
                {"role": "user", "content": "Input message"},
                {"role": "assistant", "content": "I'm sorry, I couldn't find any stories about dragons."}
            ]
        }

        # Call retrieve_story
        response = await self.agent.retrieve_story(self.user_message, self.params)

        # Check that the LangChain agent was initialized and invoked
        mock_init_agent.assert_called_once()
        self.agent.agent.ainvoke.assert_called_once()

        # Check the response
        self.assertEqual(response.detected_intent, IntentType.STORY)
        self.assertIn("error", response.metadata)
        self.assertEqual(response.metadata["error"], "no_stories_found")

    def test_format_story_for_display(self):
        """Test that _format_story_for_display correctly formats story data"""
        formatted = self.agent._format_story_for_display(self.mock_story)

        self.assertEqual(formatted['title'], 'The Friendly Dragon')
        self.assertEqual(formatted['moral'], 'Kindness and friendship')
        self.assertEqual(formatted['setting'], 'Magical Forest')
        self.assertEqual(formatted['duration'], 5)
        self.assertEqual(formatted['age_range'], '4-8 years')
        self.assertEqual(formatted['content'], 'Once upon a time, there was a friendly dragon named Puff...')
        self.assertEqual(len(formatted['discussion']), 2)
        self.assertEqual(formatted['characters'][0]['name'], 'Puff')


# Run the tests
if __name__ == "__main__":
    # Create and run the test suite with async support
    async def run_tests():
        suite = unittest.TestLoader().loadTestsFromTestCase(TestStoryAgentLangChain)
        runner = unittest.TextTestRunner()
        return runner.run(suite)

    asyncio.run(run_tests())