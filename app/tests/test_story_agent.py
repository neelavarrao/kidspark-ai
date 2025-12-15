"""
Tests for the Story Agent functionality
"""

import unittest
import os
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime
import sys

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.backend.agents.specialized.story_agent import StoryAgent
from app.backend.agents.models.intent import UserMessage, IntentType

class TestStoryAgent(unittest.TestCase):
    """Tests for the StoryAgent class"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a patched version of the agent
        self.patcher = patch.multiple(
            'app.backend.agents.specialized.story_agent.StoryAgent',
            _get_embedding=AsyncMock(),
            _retrieve_stories=AsyncMock(),
            _rerank_stories=AsyncMock(),
            _check_user_story_history=MagicMock(),
            _record_story_shown=MagicMock(),
        )
        self.patcher.start()

        # Initialize the agent with our patches
        self.agent = StoryAgent()

        # Create a mock user message
        self.user_message = UserMessage(
            content="Can you tell me a bedtime story about dragons?",
            user_id="test-user-123",
            message_id="test-message-123",
            timestamp=datetime.utcnow()
        )

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

    def tearDown(self):
        """Tear down test fixtures"""
        self.patcher.stop()

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

    async def test_retrieve_story_success(self):
        """Test story retrieval when stories are found"""
        # Set up mock returns
        self.agent._check_user_story_history.return_value = []
        self.agent._retrieve_stories.return_value = [self.mock_story]
        self.agent._rerank_stories.return_value = [self.mock_story]

        # Call the method
        response = await self.agent.retrieve_story(self.user_message, {'themes': ['dragons']})

        # Check that the response has the expected structure
        self.assertEqual(response.detected_intent, IntentType.STORY)
        self.assertIn('The Friendly Dragon', response.content)
        self.assertEqual(response.metadata['display_type'], 'story')
        self.assertEqual(response.metadata['story_data']['title'], 'The Friendly Dragon')

        # Check that the story was recorded as shown
        self.agent._record_story_shown.assert_called_once_with('test-user-123', 1)

    async def test_retrieve_story_no_stories(self):
        """Test story retrieval when no stories are found"""
        # Set up mock returns
        self.agent._check_user_story_history.return_value = []
        self.agent._retrieve_stories.return_value = []

        # Call the method
        response = await self.agent.retrieve_story(self.user_message, {'themes': ['dragons']})

        # Check that the response has a fallback message
        self.assertEqual(response.detected_intent, IntentType.STORY)
        self.assertIn("I'm sorry, I couldn't find a story", response.content)
        self.assertIn('error', response.metadata)
        self.assertEqual(response.metadata['error'], 'no_stories_found')

    async def test_avoid_repeated_stories(self):
        """Test that stories already shown are avoided"""
        # Create two stories
        story1 = dict(self.mock_story)
        story2 = dict(self.mock_story)
        story2['id'] = 2
        story2['story_title'] = 'Dragon Mountain'

        # Set up mock returns - story 1 has been shown before
        self.agent._check_user_story_history.return_value = [1]
        self.agent._retrieve_stories.return_value = [story1, story2]
        self.agent._rerank_stories.return_value = [story1, story2]

        # Call the method
        response = await self.agent.retrieve_story(self.user_message, {'themes': ['dragons']})

        # Check that story2 was selected instead of story1
        self.assertIn('Dragon Mountain', response.content)
        self.assertEqual(response.metadata['story_data']['title'], 'Dragon Mountain')

        # Check that the story was recorded as shown
        self.agent._record_story_shown.assert_called_once_with('test-user-123', 2)

# Run the tests
if __name__ == '__main__':
    unittest.main()