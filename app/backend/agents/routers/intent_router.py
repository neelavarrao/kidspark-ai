import re
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from openai import OpenAI
import os

from app.backend.agents.models.intent import Intent, IntentType, IntentDetectionResult, UserMessage
from app.backend.services.supabase_service import get_supabase_client

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class IntentRouter:
    """
    Intent Router for KidSpark AI that determines what the user is asking for.
    Uses regex patterns first, then falls back to LLM classification for more complex queries.
    """

    def __init__(self):
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.supabase = get_supabase_client()

        # Define regex patterns for each intent
        self.patterns = {
            IntentType.ACTIVITY: [
                r"(activity|activities|things to do|what can we do|ideas for|suggest|recommend)",
                r"(something to do|craft|game|play|fun)",
                r"(bored|activity for my child|activity for my kid)",
            ],
            IntentType.STORY: [
                r"\b(story|stories)\b",  # Match single word "story" or "stories"
                r"tell.*story",  # Match variations of "tell me a story"
                r"(bedtime|fairy|short|long).*stor(y|ies)",  # Match "bedtime story", "fairy stories", etc.
                r"(read|tell).*book",  # Match "read a book", "tell me a book", etc.
                r"(fairy tale|tell a tale|once upon a time)",
                r"(bedtime|sleep|naptime).*(story|read|book)",
            ],
            IntentType.WHY: [
                r"(why|how come|what is|explain|how does)",
                r"(reason for|cause of|why is|why are|why do|why does)",
                r"\bwhy\b.*\?",
            ],
            IntentType.GREETING: [
                r"(hello|hi|hey|good morning|good afternoon|good evening)",
                r"(howdy|greetings|what's up|nice to meet you)"
            ]
        }

    def _extract_parameters(self, message: str, intent_type: IntentType) -> Dict:
        """
        Extract parameters from the message based on intent type
        """
        params = {}

        # Extract parameters for ACTIVITY intent
        if intent_type == IntentType.ACTIVITY:
            # Look for age
            age_match = re.search(r'(\d+)[- ]*(year|month)s?[- ]*(old)?', message, re.I)
            if age_match:
                params["age"] = int(age_match.group(1))
                params["age_unit"] = age_match.group(2).lower()

            # Look for time available
            time_match = re.search(r'(\d+)[- ]*(minute|hour|day)s?', message, re.I)
            if time_match:
                params["time"] = int(time_match.group(1))
                params["time_unit"] = time_match.group(2).lower()

            # Look for indoor/outdoor
            if re.search(r'indoor|inside', message, re.I):
                params["location"] = "indoor"
            elif re.search(r'outdoor|outside', message, re.I):
                params["location"] = "outdoor"

        # Extract parameters for STORY intent
        elif intent_type == IntentType.STORY:
            # Look for theme
            theme_matches = []
            themes = ["adventure", "princess", "dinosaur", "space", "animal",
                      "farm", "ocean", "jungle", "magic", "superhero"]

            for theme in themes:
                if re.search(rf'\b{theme}\b', message, re.I):
                    theme_matches.append(theme)

            if theme_matches:
                params["themes"] = theme_matches

            # Look for length
            if re.search(r'short|quick|brief', message, re.I):
                params["length"] = "short"
            elif re.search(r'long|detailed', message, re.I):
                params["length"] = "long"

        return params

    def _detect_intent_by_regex(self, message: str) -> Tuple[Optional[Intent], List[Intent]]:
        """
        Detect intent using regex patterns
        Returns the primary intent and a list of alternative intents
        """
        # Check all patterns and compute confidence based on number of matches
        intent_scores = {}
        for intent_type, patterns in self.patterns.items():
            match_count = 0
            for pattern in patterns:
                if re.search(pattern, message, re.I):
                    match_count += 1

            if match_count > 0:
                # Calculate confidence based on match count and input specificity
                # Single word inputs like "story" get higher confidence
                words = len(message.strip().split())
                if words <= 2 and match_count > 0:
                    # Short inputs with matches get high confidence
                    confidence = min(1.0, 0.8 + 0.1 * match_count)
                else:
                    # Longer inputs use ratio-based confidence
                    confidence = min(1.0, 0.6 + (0.4 * match_count / len(patterns)))

                intent_scores[intent_type] = confidence

        # Sort intents by confidence
        sorted_intents = sorted(
            intent_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # Create intent objects
        intents = []
        primary_intent = None

        for i, (intent_type, confidence) in enumerate(sorted_intents):
            params = self._extract_parameters(message, intent_type)
            intent = Intent(
                type=intent_type,
                confidence=confidence,
                detected_params=params,
                raw_input=message,
                detection_method="regex",
                timestamp=datetime.utcnow()
            )

            if i == 0 and confidence >= 0.5:  # First intent with high confidence
                primary_intent = intent
            else:
                intents.append(intent)

        return primary_intent, intents

    def _detect_intent_by_llm(self, message: str) -> Intent:
        """
        Detect intent using LLM when regex patterns are insufficient
        """
        try:
            logger.info("Using LLM for intent detection")

            # Define system prompt for intent detection with specific instructions for mixed inputs
            prompt = f"""
            You are an intent classifier for KidSpark AI, a children's assistant. Classify the user's message into one of these intents:

            1. "activity" - User is asking for activity suggestions or things to do with children
            2. "story" - User is asking for a bedtime story or narrative
            3. "why" - User is asking a question seeking an explanation (typically starting with "why" or "how")
            4. "greeting" - User is just saying hello or greeting
            5. "unknown" - None of the above

            IMPORTANT: For mixed inputs that mention multiple intents, prioritize the following:
            - If the message contains a clear request for a story (e.g., "tell me a story"), classify as "story" even if other intents are present
            - If the message mentions being "bored" AND asks for a story, classify as "story" with high confidence
            - If the user mentions being "bored" without specifying what they want, classify as "activity"
            - Explicit requests (e.g., "tell me a story", "explain why", "suggest an activity") take precedence over implied needs

            Respond ONLY with the intent label and a confidence score between 0.0 and 1.0 in this format: "intent:confidence"
            For example: "activity:0.95" or "unknown:0.3"
            """

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Using a smaller model for efficiency
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0,
                max_tokens=20
            )

            # Parse response
            result_text = response.choices[0].message.content.strip()
            intent_match = re.match(r"(\w+):(0\.\d+)", result_text)

            if intent_match:
                intent_str = intent_match.group(1)
                confidence = float(intent_match.group(2))

                # Map to our enum
                try:
                    intent_type = IntentType(intent_str)
                except ValueError:
                    intent_type = IntentType.UNKNOWN

                # Extract parameters if it's a known intent
                params = {}
                if intent_type != IntentType.UNKNOWN:
                    params = self._extract_parameters(message, intent_type)

                return Intent(
                    type=intent_type,
                    confidence=confidence,
                    detected_params=params,
                    raw_input=message,
                    detection_method="llm",
                    timestamp=datetime.utcnow()
                )
            else:
                # Fallback if response doesn't match expected format
                return Intent(
                    type=IntentType.UNKNOWN,
                    confidence=0.3,
                    detected_params={},
                    raw_input=message,
                    detection_method="llm_fallback",
                    timestamp=datetime.utcnow()
                )

        except Exception as e:
            logger.error(f"Error using LLM for intent detection: {str(e)}")
            return Intent(
                type=IntentType.UNKNOWN,
                confidence=0.1,
                detected_params={},
                raw_input=message,
                detection_method="llm_error",
                timestamp=datetime.utcnow()
            )

    def detect_intent(self, message: UserMessage) -> IntentDetectionResult:
        """
        Detect the user's intent from their message
        Uses the LLM for all intent detection for better reliability
        """
        message_text = message.content
        message_id = message.message_id or str(uuid.uuid4())
        user_id = message.user_id

        # Always use LLM for intent detection
        primary_intent = self._detect_intent_by_llm(message_text)
        alternative_intents = []

        # If LLM couldn't give a high confidence result, try regex as backup
        if primary_intent.confidence < 0.5:
            regex_intent, regex_alternatives = self._detect_intent_by_regex(message_text)

            if regex_intent and regex_intent.confidence > primary_intent.confidence:
                alternative_intents.append(primary_intent)  # Move LLM result to alternatives
                primary_intent = regex_intent
                alternative_intents.extend(regex_alternatives)
            elif regex_intent:
                # Keep LLM intent as primary but add regex results to alternatives
                alternative_intents.append(regex_intent)
                alternative_intents.extend(regex_alternatives)

        # If we still have no good primary intent, use UNKNOWN
        if primary_intent.confidence < 0.3:
            primary_intent = Intent(
                type=IntentType.UNKNOWN,
                confidence=0.3,
                detected_params={},
                raw_input=message_text,
                detection_method="fallback",
                timestamp=datetime.utcnow()
            )

        # Create the result
        result = IntentDetectionResult(
            primary_intent=primary_intent,
            alternative_intents=alternative_intents,
            user_id=user_id,
            message_id=message_id
        )

        # Log the intent detection
        self._log_intent_detection(result)

        return result

    def _log_intent_detection(self, result: IntentDetectionResult):
        """
        Log the intent detection result to Supabase
        """
        try:
            log_entry = {
                'message_id': result.message_id,
                'user_id': result.user_id,
                'primary_intent': result.primary_intent.type,
                'confidence': result.primary_intent.confidence,
                'detection_method': result.primary_intent.detection_method,
                'timestamp': datetime.utcnow().isoformat(),
                'raw_input': result.primary_intent.raw_input[:500]  # Truncate if too long
            }

            self.supabase.table("intent_logs").insert(log_entry).execute()
        except Exception as e:
            logger.error(f"Error logging intent detection: {str(e)}")
            # Continue even if logging fails